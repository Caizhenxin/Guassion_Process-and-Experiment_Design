/** 作业面板 · 宿主侧：把 `$DSH_HOME/jobboard/jobs/<id>/status.json` 读成一个只读 JSON 接口。
 *
 * 约定见 `1_Code/Tools/jobstatus.py`：任何作业只要写 status.json，就会自动出现在面板里。
 * 这里只做两件事：扫目录、把 mtime 换算成「心跳多久以前」，前端据此判断是否掉线。
 */

import { readdir, readFile, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export const name = "@local/dsh-jobboard";

/** 需要 webServer 服务来注册 HTTP 路由。 */
export const inject = ["webServer"];

const PREFIX = "/jobboard-api";

/** 作业根目录：环境变量优先，其次 `$DSH_HOME/jobboard/jobs`。 */
function jobsRoot() {
	if (process.env.DSH_JOBBOARD_DIR) return process.env.DSH_JOBBOARD_DIR;
	const home = process.env.DSH_HOME
		|| join(homedir(), "AppData", "Roaming", "dsh-desktop", "harness");
	return join(home, "jobboard", "jobs");
}

/** 心跳超过这个秒数就认为「可能掉线」。 */
const STALE_SECONDS = 600;

async function collect(root) {
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
		let mtime;
		try {
			[text, mtime] = await Promise.all([readFile(file, "utf8"), stat(file)]);
		} catch {
			continue;
		}
		let data;
		try {
			data = JSON.parse(text);
		} catch {
			continue;
		}
		const age = Math.max(0, Math.round((now - mtime.mtimeMs) / 1000));
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

function sendJson(res, code, payload) {
	const body = JSON.stringify(payload);
	res.writeHead(code, {
		"Content-Type": "application/json; charset=utf-8",
		"Content-Length": Buffer.byteLength(body),
		"Cache-Control": "no-store"
	});
	res.end(body);
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
			sendJson(res, 200, { ok: true, ...(await collect(jobsRoot())), stale_seconds: STALE_SECONDS });
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
