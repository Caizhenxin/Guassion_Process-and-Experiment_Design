window.__ModuleLoader__.load({
	id: "@local/dsh-jobboard",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });

		const React = require("react");
		const h = React.createElement;

		/** 词典命名空间（侧边栏标签、面板标题共用）。 */
		const NS = "jobboard";
		/** 侧边栏条目与主面板共用的 id。 */
		const PANEL_ID = "jobboard";
		/** 宿主侧提供的只读接口（见 lib/index.mjs）：作业 + 窗口 + 进程一次取回。 */
		const API = "/jobboard-api/state";

		/** 需要的服务：插槽、语言、布局。 */
		const inject = ["slots", "locale", "layout"];

		/* ---------------- 取数 ---------------- */

		function useSnapshot(intervalMs) {
			const empty = { loading: true, jobs: [], windows: [], procs: [], root: "", error: null, at: 0, procTotal: 0 };
			const [state, setState] = React.useState(empty);
			React.useEffect(() => {
				let stop = false;
				async function tick() {
					try {
						const res = await fetch(API, { cache: "no-store" });
						const body = await res.json();
						if (stop) return;
						if (!body.ok) throw new Error(body.error || "接口返回失败");
						setState({
							loading: false,
							jobs: body.jobs || [],
							windows: body.windows || [],
							procs: body.procs || [],
							root: body.jobs_root || "",
							procTotal: body.proc_total || 0,
							error: null,
							at: Date.now()
						});
					} catch (error) {
						if (stop) return;
						setState((prev) => ({ ...prev, loading: false, error: String(error && error.message ? error.message : error) }));
					}
				}
				void tick();
				const timer = setInterval(() => void tick(), intervalMs);
				return () => {
					stop = true;
					clearInterval(timer);
				};
			}, [intervalMs]);
			return state;
		}

		/* ---------------- 小工具 ---------------- */

		function humanAge(sec) {
			if (sec == null) return "—";
			if (sec < 90) return sec + " 秒前";
			if (sec < 5400) return Math.round(sec / 60) + " 分钟前";
			return (sec / 3600).toFixed(1) + " 小时前";
		}

		function humanEta(sec) {
			if (!sec || sec <= 0) return "—";
			const m = Math.round(sec / 60);
			if (m < 60) return m + " 分钟";
			return (m / 60).toFixed(1) + " 小时";
		}

		const TONE = {
			running: { bg: "#ddf4ff", fg: "#0969da", border: "#b6e3ff", text: "运行中" },
			stalled: { bg: "#fff1e5", fg: "#bc4c00", border: "#ffd8a8", text: "心跳停了" },
			done: { bg: "#dafbe1", fg: "#1a7f37", border: "#aceebb", text: "已完成" },
			failed: { bg: "#ffebe9", fg: "#cf222e", border: "#ffcecb", text: "失败" }
		};

		function tone(job) {
			if (job.stale) return TONE.stalled;
			return TONE[job.state] || { bg: "#f6f8fa", fg: "#59636e", border: "#d0d7de", text: job.state || "未知" };
		}

		const styles = {
			page: {
				display: "flex", flexDirection: "column", gap: "14px",
				padding: "22px 26px", height: "100%", overflow: "auto",
				fontSize: "13px", lineHeight: "1.6", color: "var(--dsw-alias-fg, #1f2328)"
			},
			card: {
				border: "1px solid var(--dsw-alias-border, #d0d7de)", borderRadius: "10px",
				padding: "14px 16px", display: "flex", flexDirection: "column", gap: "8px",
				background: "var(--dsw-alias-bg, #fff)"
			},
			chip: { display: "inline-block", padding: "1px 9px", borderRadius: "999px", fontSize: "12px", border: "1px solid" },
			barOuter: { height: "7px", borderRadius: "999px", background: "#eaeef2", overflow: "hidden" },
			barInner: { height: "100%", borderRadius: "999px", background: "#2da44e" },
			muted: { color: "var(--dsw-alias-fg-muted, #59636e)" },
			mono: { fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace", fontSize: "12px", whiteSpace: "pre-wrap", margin: 0 }
		};

		function JobCard({ job }) {
			const t = tone(job);
			const total = job.total;
			const done = job.done ?? 0;
			const pct = total ? Math.min(100, Math.round((done / total) * 100)) : null;
			return h("div", { style: styles.card },
				h("div", { style: { display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" } },
					h("strong", { style: { fontSize: "14px" } }, job.title || job.id),
					h("span", {
						style: { ...styles.chip, background: t.bg, color: t.fg, borderColor: t.border }
					}, t.text),
					h("span", { style: styles.muted }, "心跳 ", humanAge(job.age_seconds)),
					total ? h("span", { style: styles.muted }, "进度 ", done, "/", total) : null,
					job.eta_seconds ? h("span", { style: styles.muted }, "剩余约 ", humanEta(job.eta_seconds)) : null),
				job.step ? h("div", null, job.step) : null,
				pct !== null
					? h("div", { style: styles.barOuter }, h("div", { style: { ...styles.barInner, width: pct + "%" } }))
					: null,
				Array.isArray(job.tail) && job.tail.length
					? h("pre", { style: { ...styles.mono, ...styles.muted, background: "#f6f8fa", padding: "8px 10px", borderRadius: "8px", overflowX: "auto" } },
						job.tail.join("\n"))
					: null,
				job.relaunch
					? h("div", { style: styles.muted },
						"掉线可重跑：", h("code", { style: styles.mono }, job.relaunch))
					: null);
		}

		/* ---------------- 面板 ---------------- */

		function Section({ title, hint, children }) {
			return h("div", { style: styles.card },
				h("div", { style: { display: "flex", alignItems: "baseline", gap: "10px", flexWrap: "wrap" } },
					h("strong", { style: { fontSize: "14px" } }, title),
					hint ? h("span", { style: { ...styles.muted, fontSize: "12px" } }, hint) : null),
				children);
		}

		function WindowRow({ win, procs }) {
			const live = procs.filter((p) => p.project && win.cwd && win.cwd.endsWith(p.project));
			return h("div", { style: { display: "flex", gap: "10px", alignItems: "baseline", flexWrap: "wrap", padding: "3px 0" } },
				h("span", { style: { width: "104px", ...styles.muted, fontSize: "12px" } }, humanAge(win.ago_seconds)),
				h("span", { style: { minWidth: "180px" } }, win.title),
				h("code", { style: { ...styles.mono, ...styles.muted } }, win.sid),
				win.cwd ? h("span", { style: { ...styles.mono, ...styles.muted, fontSize: "11px" } }, win.cwd) : null,
				live.length ? h("span", { style: { ...styles.chip, background: "#ddf4ff", color: "#0969da", borderColor: "#b6e3ff" } }, "跑着 " + live.length + " 个进程") : null);
		}

		function ProcRow({ proc }) {
			return h("div", { style: { display: "flex", gap: "10px", alignItems: "baseline", flexWrap: "wrap", padding: "3px 0" } },
				h("span", { style: { width: "88px", ...styles.muted, fontSize: "12px" } }, humanAge(proc.age_seconds)),
				h("span", { style: { width: "62px" } }, proc.name),
				h("code", { style: { ...styles.mono, ...styles.muted } }, "pid " + proc.pid),
				proc.project ? h("span", { style: { ...styles.chip, background: "#f6f8fa", color: "#59636e", borderColor: "#d0d7de" } }, proc.project) : null,
				h("code", { style: { ...styles.mono, ...styles.muted, fontSize: "11px", maxWidth: "620px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, proc.cmd));
		}

		function JobBoardPage() {
			const s = useSnapshot(3000);
			const running = s.jobs.filter((j) => j.state === "running" && !j.stale).length;

			return h("div", { style: styles.page },
				h("div", { style: { display: "flex", alignItems: "baseline", gap: "12px", flexWrap: "wrap" } },
					h("h2", { style: { margin: 0, fontSize: "17px" } }, "作业面板"),
					h("span", { style: styles.muted }, "作业 ", running, " 个在跑 / 共 ", s.jobs.length),
					h("span", { style: styles.muted }, "· 进程 ", s.procs.length, " / ", s.procTotal),
					h("span", { style: styles.muted }, "· 窗口 ", s.windows.length),
					h("span", { style: { ...styles.muted, fontSize: "12px" } }, "（每 3 秒刷新）")),

				s.error
					? h("div", { style: { ...styles.card, borderColor: "#ffcecb", background: "#ffebe9" } },
						h("strong", null, "读不到状态"),
						h("div", null, s.error),
						h("div", { style: styles.muted },
							"常见原因：宿主侧接口没加载（重启 DSH 后才会生效）。"))
					: null,

				h(Section, { title: "窗口", hint: "最近的 DSH 会话（标题 · 工作目录 · 最后活动）" },
					s.windows.length === 0
						? h("div", { style: styles.muted }, s.loading ? "加载中…" : "没有读到窗口")
						: s.windows.slice(0, 12).map((w) => h(WindowRow, { key: w.sid, win: w, procs: s.procs }))),

				h(Section, { title: "进程", hint: "正在跑的长进程（时长 · pid · 项目 · 命令行）" },
					s.procs.length === 0
						? h("div", { style: styles.muted }, s.loading ? "加载中…" : "没有 45 秒以上的进程")
						: s.procs.map((p) => h(ProcRow, { key: p.pid, proc: p }))),

				s.jobs.length > 0
					? h(Section, { title: "作业", hint: "自报进度的作业（jobstatus.py 写 status.json）" },
						s.jobs.map((job) => h(JobCard, { key: job.id + ":" + job.started_at, job })))
					: h(Section, { title: "作业", hint: "还没有任何作业自报进度" },
						h("div", { style: styles.muted },
							"让脚本用 ", h("code", { style: styles.mono }, "jobstatus.Job(...)"),
							" 写一个 status.json，这里就会出进度卡片。")),

				s.loading ? h("div", { style: styles.muted }, "加载中…") : null);
		}

		/** 侧边栏图标。 */
		function JobBoardIcon() {
			return h("span", { style: { fontSize: "16px", lineHeight: "1" } }, "⏱");
		}

		/** 注册侧边栏条目与主面板。 */
		function apply(ctx) {
			ctx.slots.inject("sidebar.panellist", () => ctx.slots.register({
				name: "sidebar.panellist",
				id: PANEL_ID,
				order: 0,
				label: () => "作业",
				locale: NS
			}, JobBoardIcon));

			ctx.slots.inject("main", function* () {
				yield ctx.slots.register({
					name: "main",
					key: PANEL_ID,
					locale: NS,
					inject: () => ({})
				}, JobBoardPage);
			});
		}

		exports.NS = NS;
		exports.PANEL_ID = PANEL_ID;
		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});
