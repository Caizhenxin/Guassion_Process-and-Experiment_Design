/** 宿主侧离线自测：不启动 DSH，用假的 ctx / webServer 跑一遍接口。
 *
 *   node 1_Code/Tools/dsh-jobboard/test_host.mjs
 *
 * 验的是四件事：① 插件导出 apply/inject；② 能拿到 webServer 并注册路由；
 * ③ GET /jobboard-api/jobs 返回合法 JSON；④ 非 GET 被拒、未知路径 404。
 */

import { apply, inject, name } from "./lib/index.mjs";

const asserts = [];
function check(label, ok, detail) {
	asserts.push({ label, ok, detail });
	console.log(`${ok ? "✅" : "❌"} ${label}${detail ? "  " + detail : ""}`);
}

let registered = null;
const server = {
	register(route) {
		registered = route;
		return () => {};
	}
};

const webCtx = {
	get: (key) => (key === "webServer" ? server : undefined),
	effect: (fn) => {
		fn();
		return () => {};
	}
};

const ctx = {
	inject: (deps, cb) => {
		check("inject 声明里含 webServer", deps.includes("webServer"), JSON.stringify(deps));
		cb(webCtx);
	}
};

apply(ctx);
check("插件名正确", name === "@local/dsh-jobboard", name);
check("inject 导出含 webServer", Array.isArray(inject) && inject.includes("webServer"));
check("注册到 webServer", Boolean(registered), registered && registered.path);
check("注册类型是 prefix", registered?.kind === "prefix");

function call(method, path) {
	return new Promise((resolve) => {
		const chunks = [];
		const res = {
			statusCode: 0,
			headers: {},
			writeHead(code, headers) {
				this.statusCode = code;
				this.headers = headers ?? {};
				return this;
			},
			end(body) {
				if (body) chunks.push(Buffer.from(body));
				resolve({
					code: this.statusCode,
					headers: this.headers,
					text: Buffer.concat(chunks).toString("utf8")
				});
			}
		};
		registered.handler({ method, url: path, headers: {} }, res);
	});
}

const jobs = await call("GET", "/jobboard-api/jobs");
check("GET /jobs 返回 200", jobs.code === 200, `code=${jobs.code}`);
let body = null;
try {
	body = JSON.parse(jobs.text);
} catch {}
check("响应是 JSON", Boolean(body));
check("带 root 字段", typeof body?.root === "string", body?.root);
check("jobs 是数组", Array.isArray(body?.jobs), `n=${body?.jobs?.length}`);
if (body?.jobs?.length) {
	const j = body.jobs[0];
	const keys = ["id", "state", "done", "total", "age_seconds", "stale"];
	check("作业字段齐全", keys.every((k) => k in j), keys.filter((k) => !(k in j)).join(",") || "全有");
	console.log(`   首个作业：${j.title} ${j.state} ${j.done}/${j.total}（心跳 ${j.age_seconds}s）`);
}

const state = await call("GET", "/jobboard-api/state");
check("GET /state 返回 200", state.code === 200, `code=${state.code}`);
let snapshot = null;
try {
	snapshot = JSON.parse(state.text);
} catch {}
check("state 是 JSON 且 ok", snapshot?.ok === true);
for (const key of ["jobs", "windows", "procs"]) {
	check(`state.${key} 是数组`, Array.isArray(snapshot?.[key]), `n=${snapshot?.[key]?.length}`);
}
if (snapshot?.windows?.length) {
	const w = snapshot.windows[0];
	check("窗口字段齐全", ["sid", "title", "cwd", "last", "ago_seconds"].every((k) => k in w),
		`${w.title} · ${w.sid} · ${w.cwd || "(无 cwd)"}`);
}
if (snapshot?.procs?.length) {
	const p = snapshot.procs[0];
	check("进程字段齐全", ["pid", "name", "age_seconds", "cmd"].every((k) => k in p),
		`${p.name} pid=${p.pid} ${Math.round((p.age_seconds ?? 0) / 60)} 分钟`);
}

const health = await call("GET", "/jobboard-api/health");
check("GET /health 返回 200", health.code === 200, health.text.slice(0, 60));

const bad = await call("GET", "/jobboard-api/nope");
check("未知路径 404", bad.code === 404, `code=${bad.code}`);

const post = await call("POST", "/jobboard-api/jobs");
check("POST 被拒 405", post.code === 405, `code=${post.code}`);

const failed = asserts.filter((a) => !a.ok).length;
console.log(`\n${asserts.length - failed}/${asserts.length} 项通过`);
process.exit(failed ? 1 : 0);
