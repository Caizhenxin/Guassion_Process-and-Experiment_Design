/** 作业面板 · 宿主侧：把「什么在跑 / 跑了多久 / 属于哪个窗口」做成只读 JSON。
 *
 * 三个数据源，各管一段事实：
 *   1. `$DSH_HOME/jobboard/jobs/<id>/status.json` —— 自愿上报的作业进度（见 1_Code/Tools/jobstatus.py）
 *   2. `$DSH_HOME/storages/session_projcache/sessions/session-*.json` 头部 8 KB —— 窗口标题 / 工作目录 / 创建时间
 *   3. `Win32_Process` —— 进程表（pid、命令行、创建时间）；Windows 拿不到「属于哪个 GUI 窗口」，只能做项目级归属
 *
 * 之所以放在宿主侧：浏览器端既读不到磁盘进程表，也读不到会话投影目录。
 */

import { execFile } from "node:child_process";
import { open, readdir, readFile, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, join } from "node:path";

export const name = "@local/dsh-jobboard";

/** 需要 webServer 服务来注册 HTTP 路由。 */
export const inject = ["webServer"];

const PREFIX = "/jobboard-api";
const STALE_SECONDS = 600;
const WINDOW_HEAD_BYTES = 8192;
const WINDOW_FILES = 40;
const PROC_CACHE_MS = 5000;

function dshHome() {
	return process.env.DSH_HOME
		|| join(homedir(), "AppData", "Roaming", "dsh-desktop", "harness");
}

/** 作业根目录：环境变量优先，其次 `$DSH_HOME/jobboard/jobs`。 */
function jobsRoot() {
	return process.env.DSH_JOBBOARD_DIR || join(dshHome(), "jobboard", "jobs");
}

/* ---------------- 1. 自报作业 ---------------- */

async function collectJobs(root) {
	const out = [];
	let names = [];
	try {
		names = await readdir(root);
	} catch (error) {
		if (error.code === "ENOENT") return { root, jobs: [], error: "作业目录还不存在（还没有作业写过 status.json）" };
		throw error;
	}
	const now = Date.now();
	for (const dir of names) {
		const file = join(root, dir, "status.json");
		let text;
		let info;
		try {
			[text, info] = await Promise.all([readFile(file, "utf8"), stat(file)]);
		} catch {
			continue;
		}
		let data;
		try {
			data = JSON.parse(text);
		} catch {
			continue;
		}
		const age = Math.max(0, Math.round((now - info.mtimeMs) / 1000));
		out.push({
			...data,
			id: data.id ?? dir,
			age_seconds: age,
			stale: data.state === "running" && age > STALE_SECONDS
		});
	}
	out.sort((a, b) => {
		const running = Number(b.state === "running") - Number(a.state === "running");
		if (running !== 0) return running;
		return String(a.started_at ?? "").localeCompare(String(b.started_at ?? ""));
	});
	return { root, jobs: out };
}

/* ---------------- 2. DSH 窗口（会话投影头部） ---------------- */

const CWD_RE = /"cwd"\s*:\s*"((?:[^"\\]|\\.)*)"/;
const TITLE_RE = /"title"\s*:\s*\{[^{}]*?"val"\s*:\s*"((?:[^"\\]|\\.)*)"/;
const CREATED_RE = /"createdAt"\s*:\s*"([^"]+)"/;

function unescapeJson(text) {
	try {
		return JSON.parse(`"${text}"`);
	} catch {
		return text;
	}
}

function stamp(ms) {
	const pad = (n) => String(n).padStart(2, "0");
	const d = new Date(ms);
	return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function isoStamp(value) {
	const ms = Date.parse(value ?? "");
	return Number.isNaN(ms) ? "" : stamp(ms);
}

async function readHead(file) {
	const handle = await open(file, "r");
	try {
		const buffer = Buffer.alloc(WINDOW_HEAD_BYTES);
		const { bytesRead } = await handle.read(buffer, 0, WINDOW_HEAD_BYTES, 0);
		return buffer.subarray(0, bytesRead).toString("utf8");
	} finally {
		await handle.close();
	}
}

async function collectWindows() {
	const dir = join(dshHome(), "storages", "session_projcache", "sessions");
	let names = [];
	try {
		names = (await readdir(dir)).filter((n) => n.endsWith(".json"));
	} catch (error) {
		return { dir, windows: [], error: `读不到会话投影：${error.code ?? error}` };
	}
	const stats = [];
	for (const n of names) {
		const path = join(dir, n);
		try {
			stats.push({ path, mtimeMs: (await stat(path)).mtimeMs });
		} catch {
			continue;
		}
	}
	stats.sort((a, b) => b.mtimeMs - a.mtimeMs);
	const windows = [];
	for (const item of stats.slice(0, WINDOW_FILES)) {
		let head;
		try {
			head = await readHead(item.path);
		} catch {
			continue;
		}
		const cwd = CWD_RE.exec(head)?.[1];
		const title = TITLE_RE.exec(head)?.[1];
		const created = CREATED_RE.exec(head)?.[1];
		windows.push({
			sid: basename(item.path).replace(/^session-/, "").replace(/\.json$/, "").slice(0, 8),
			title: title ? unescapeJson(title) : "(无标题)",
			cwd: cwd ? unescapeJson(cwd) : "",
			created: isoStamp(created),
			last: stamp(item.mtimeMs),
			ago_seconds: Math.max(0, Math.round((Date.now() - item.mtimeMs) / 1000))
		});
	}
	return { dir, windows };
}

/* ---------------- 3. 进程表 ---------------- */

const PROC_SCRIPT = [
	"$ErrorActionPreference='SilentlyContinue';",
	"Get-CimInstance Win32_Process",
	"| Where-Object { $_.Name -match '^(python|pythonw|node|cmd|powershell|pwsh|jupyter|DSH|electron)' }",
	"| Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine",
	"| ConvertTo-Json -Compress -Depth 3"
].join(" ");

const NOISE = /Get-CimInstance|ConvertTo-Json|running\.py|jobboard-api|McAfee|Adobe|MicrosoftEdge|WmiPrvSE/i;

let procCache = { at: 0, rows: [] };

function runProcScan() {
	return new Promise((resolve) => {
		execFile(
			"powershell",
			["-NoProfile", "-NoLogo", "-NonInteractive", "-Command", PROC_SCRIPT],
			{ timeout: 15000, windowsHide: true, maxBuffer: 8 * 1024 * 1024 },
			(error, stdout) => {
				if (error) {
					resolve([]);
					return;
				}
				let parsed;
				try {
					parsed = JSON.parse(stdout || "[]");
				} catch {
					resolve([]);
					return;
				}
				const list = Array.isArray(parsed) ? parsed : [parsed];
				const now = Date.now();
				resolve(list.map((p) => {
					const raw = String(p.CreationDate ?? "");
					let startMs = NaN;
					const dated = /\/Date\((\d+)\)\//.exec(raw);
					if (dated) startMs = Number(dated[1]);
					else if (raw) startMs = Date.parse(raw);
					return {
						pid: p.ProcessId,
						ppid: p.ParentProcessId,
						name: String(p.Name ?? "").replace(/\.exe$/i, ""),
						age_seconds: Number.isFinite(startMs) ? Math.max(0, Math.round((now - startMs) / 1000)) : null,
						cmd: String(p.CommandLine ?? "").slice(0, 300)
					};
				}));
			}
		);
	});
}

async function collectProcs(knownCwds) {
	if (Date.now() - procCache.at > PROC_CACHE_MS) {
		procCache = { at: Date.now(), rows: await runProcScan() };
	}
	const picked = [];
	for (const row of procCache.rows) {
		if (!row.cmd || NOISE.test(row.cmd) || row.pid === process.pid) continue;
		if ((row.age_seconds ?? 0) < 45) continue;
		const project = knownCwds.find((cwd) => cwd && row.cmd.includes(cwd)) ?? "";
		picked.push({ ...row, project: project ? basename(project) : "" });
	}
	picked.sort((a, b) => (b.age_seconds ?? 0) - (a.age_seconds ?? 0));
	return { rows: picked.slice(0, 40), total: procCache.rows.length };
}

/* ---------------- 路由 ---------------- */

function sendJson(res, code, payload) {
	const body = JSON.stringify(payload);
	res.writeHead(code, {
		"Content-Type": "application/json; charset=utf-8",
		"Content-Length": Buffer.byteLength(body),
		"Cache-Control": "no-store"
	});
	res.end(body);
}

async function state() {
	const [jobState, windowState] = await Promise.all([collectJobs(jobsRoot()), collectWindows()]);
	const cwds = (windowState.windows ?? []).map((w) => w.cwd);
	const procState = await collectProcs(cwds);
	return {
		ok: true,
		at: new Date().toISOString(),
		jobs: jobState.jobs ?? [],
		jobs_root: jobState.root,
		jobs_error: jobState.error ?? null,
		windows: windowState.windows ?? [],
		windows_error: windowState.error ?? null,
		procs: procState.rows,
		proc_total: procState.total,
		stale_seconds: STALE_SECONDS
	};
}

async function handler(req, res) {
	if (req.method !== "GET" && req.method !== "HEAD") {
		res.writeHead(405, { Allow: "GET, HEAD" }).end();
		return;
	}
	const pathname = new URL(req.url ?? "/", "http://localhost").pathname;
	try {
		if (pathname === `${PREFIX}/health`) {
			sendJson(res, 200, { ok: true, root: jobsRoot() });
			return;
		}
		if (pathname === `${PREFIX}/jobs`) {
			sendJson(res, 200, { ok: true, ...(await collectJobs(jobsRoot())), stale_seconds: STALE_SECONDS });
			return;
		}
		if (pathname === `${PREFIX}/state`) {
			sendJson(res, 200, await state());
			return;
		}
		sendJson(res, 404, { ok: false, error: `未知路径 ${pathname}` });
	} catch (error) {
		sendJson(res, 500, { ok: false, error: String(error?.message ?? error) });
	}
}

export function apply(ctx) {
	ctx.inject(["webServer"], (webCtx) => {
		const server = webCtx.get("webServer");
		if (!server?.register) {
			console.error("[dsh-jobboard] 拿不到 webServer，面板将没有数据");
			return;
		}
		webCtx.effect(() => server.register({
			kind: "prefix",
			path: PREFIX,
			handler: (req, res) => {
				void handler(req, res);
			}
		}), "@local/dsh-jobboard: jobs api");
	});
}
