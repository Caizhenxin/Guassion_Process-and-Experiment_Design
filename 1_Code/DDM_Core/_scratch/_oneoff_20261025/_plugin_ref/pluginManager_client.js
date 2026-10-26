nableNow: () => {
							setActivation(state.install.installed);
							props.enableInstalled();
						},
						onApproveBuilds: props.approveBuildsAndRetry,
						onToggleRegistry: props.toggleRegistryOptions,
						onChooseRegistry: props.chooseRegistry,
						onChangeRegistry: props.changeRegistry,
						onUseGithubMirror: props.useGithubMirror
					}),
					state.confirm === null ? null : (0, react_jsx_runtime.jsx)(ConfirmDialog, {
						name: packageText(state.packages.find((pkg) => pkg.name === state.confirm?.packageName) ?? { name: state.confirm.packageName }, resolveText).title,
						t,
						onConfirm: props.confirm,
						onCancel: props.cancelConfirm
					})
				]
			});
		}
		//#endregion
		//#region lib/types/client/PluginRefreshToast.js
		/**
		* Display refresh failures even after navigation leaves the Plugins panel.
		* @param props - shared notice hook, dismissal action, and locale seat.
		* @returns the refresh failure toast, or null for other notices.
		*/
		function PluginRefreshToast({ usePluginManager, dismissNotice, t }) {
			const notice = usePluginManager((state) => state.notice);
			if (notice?.kind !== "refresh-failed") return null;
			return (0, react_jsx_runtime.jsx)(_deepseek_ai_dsh_client_ui_primitives.Toast, {
				text: noticeText(notice, t),
				icon: (0, react_jsx_runtime.jsx)(_deepseek_ai_dsh_client_ui_primitives.IconWarningOutlineRegular, {}),
				onDone: dismissNotice
			}, notice.seq);
		}
		//#endregion
		//#region lib/types/client/PluginsPanelIcon.js
		/**
		* Render the plugin glyph at the size the sidebar asks for.
		* @param props - the sidebar's icon share: the requested edge and whether the panel is selected.
		* @returns the icon element.
		*/
		function PluginsPanelIcon({ size }) {
			return (0, react_jsx_runtime.jsx)(_deepseek_ai_dsh_client_ui_primitives.IconPluginPinwheelOutlineRegular, { size });
		}
		//#endregion
		//#region lib/types/client/tab-ledger.js
		/** The tabs other plugins contribute to the Plugins page through `plugins.tab`, in the active locale. */
		/**
		* Project the `plugins.tab` ledger as one observable the page binds.
		* @param ctx - the page plugin's context, whose slot registry and locale the projection follows.
		* @returns the tab source; its snapshot changes only when the ledger or the locale does.
		*/
		function tabLedgerSource(ctx) {
			let version = -1;
			let revision = -1;
			let tabs = [];
			return {
				getSnapshot: () => {
					const next = ctx.slots.getVersion("plugins.tab");
					const current = ctx.locale.getSnapshot().revision;
					if (next !== version || current !== revision) {
						version = next;
						revision = current;
						tabs = ctx.slots.entries("plugins.tab").map((entry) => ({
							/* v8 ignore next -- list-slot registration requires id */
							id: entry.options.id ?? "",
							label: (0, _deepseek_ai_dsh_client_ui_slots.resolveSlotLabel)(entry.options.label) ?? ""
						}));
					}
					return tabs;
				},
				subscribe: (listener) => {
					const offs = [ctx.slots.subscribe("plugins.tab", listener), ctx.locale.subscribe(listener)];
					return () => {
						for (const off of offs) off();
					};
				}
			};
		}
		//#endregion
		//#region lib/types/client/navigation-store.js
		/** Plugin page selection shared by the page and cross-plugin navigation. */
		/**
		* Create plugin page selection before the first page render.
		* @returns the registration-owned navigation store handle.
		*/
		function createNavigationStore() {
			return (0, _deepseek_ai_dsh_client_store.defineStore)({
				init: () => ({
					view: { kind: "list" },
					tab: "installed"
				}),
				actions: {
					setView: (draft, view) => {
						draft.view = view;
					},
					setTab: (draft, tab) => {
						draft.tab = tab;
					}
				}
			});
		}
		//#endregion
		//#region lib/types/client/index.js
		/** Dictionary namespace owned by this plugin. */
		const NS = "pluginManager";
		/** The id shared by the sidebar entry and the main panel it opens. */
		const PANEL_ID = "plugins";
		/** Services required by the sidebar registration and the Remote methods; the inventory says whether the Host manages a profile. */
		const inject = [
			"slots",
			"locale",
			"remote",
			"remote.pluginManager",
			"remote.pluginInventory",
			"remote.pluginRegistryProbe",
			"configForms",
			"layout"
		];
		/**
		* Contribute the Plugins entry to the sidebar with the management page it
		* opens, and keep it current on the Host's change events.
		* @param ctx - the browser plugin context.
		*/
		function apply(ctx) {
			ctx.effect(() => ctx.locale.register(NS, {
				zh,
				en
			}), "ui-plugin-manager: dictionaries");
			const t = ctx.locale.bind(NS);
			const controller = new PluginManagerController(ctx);
			ctx.effect(() => () => {
				controller.dispose();
			}, "ui-plugin-manager: controller");
			ctx.effect(() => {
				const refresh = () => {
					if (controller.getSnapshot().status !== "idle") controller.load();
				};
				const disposers = [
					ctx.remote.$on("plugin-manager/changed", refresh),
					ctx.remote.$on("plugin-manager/install-log", (chunk) => {
						controller.appendLog(chunk);
					}),
					ctx.remote.$on("plugin-manager/install-state", (progress) => {
						controller.installProgress(progress);
					}),
					ctx.on("connection/reset", refresh)
				];
				return () => {
					for (const dispose of disposers) dispose();
				};
			}, "ui-plugin-manager: host invalidations");
			const configLedger = configLedgerSource(ctx);
			const face = controller.inject(configLedger, tabLedgerSource(ctx), (text) => ctx.locale.resolveText(text));
			ctx.slots.inject("shell.overlay", () => ctx.slots.register({
				name: "shell.overlay",
				id: "plugin-manager.refresh-toast",
				locale: NS,
				inject: () => ({
					hooks: { pluginManager: face.hooks.pluginManager },
					dismissNotice: face.dismissNotice
				})
			}, PluginRefreshToast));
			ctx.slots.inject("main", function* () {
				const handle = createNavigationStore(), instance = handle.create();
				const store = {
					...handle,
					create: () => instance
				};
				yield ctx.slots.register({
					name: "main",
					key: PANEL_ID,
					locale: NS,
					store,
					inject: () => face,
					children: {
						"plugins.add.actions": {
							kind: "list",
							scope: "root"
						},
						"plugins.tab": {
							kind: "list",
							scope: "root"
						},
						"plugins.item": {
							kind: "list",
							scope: "root"
						},
						"plugins.bundle.activation": {
							kind: "keyed",
							scope: "root"
						},
						"plugins.bundle.config": {
							kind: "keyed",
							scope: "root"
						},
						"plugins.row.config": {
							kind: "keyed",
							scope: "root"
						},
						"plugins.detail.actions": {
							kind: "list",
							scope: "root"
						},
						"plugins.detail.badge": {
							kind: "list",
							scope: "root"
						},
						"plugins.detail.section": {
							kind: "list",
							scope: "root"
						}
					}
				}, PluginManagerPage);
				yield ctx.layout.panelInfo.subscribe(() => {
					if (ctx.layout.panelInfo.getSnapshot().activePanelId !== "plugins") instance.actions.setView({ kind: "list" });
				});
				const disposeNavigation = ctx.reflect.provide("pluginNavigation", { openBundle: (packageName) => {
					ctx.layout.selectPanel(PANEL_ID);
					instance.actions.setTab("installed");
					instance.actions.setView({
						kind: "package",
						name: packageName
					});
				} });
				yield () => {
					disposeNavigation();
				};
			});
			ctx.slots.inject("sidebar.panellist", () => ctx.slots.register({
				name: "sidebar.panellist",
				id: PANEL_ID,
				order: 0,
				label: () => t("panel"),
				locale: NS
			}, PluginsPanelIcon));
		}
		//#endregion
		exports.NS = NS;
		exports.PANEL_ID = PANEL_ID;
		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});

//# sourceMappingURL=client.js.mapimport z from "@deepseek-ai/schemastery";
import { MAX_TIMER_DELAY_MS } from "@deepseek-ai/dsh-timeout";
import { Remote, TypertRemoteService } from "@deepseek-ai/dsh-typert-protocol";
//#region lib/types/index.js
/** Host registry-response probing for the plugin installation dialog. */
var __runInitializers = function(thisArg, initializers, value) {
	var useValue = arguments.length > 2;
	for (var i = 0; i < initializers.length; i++) value = useValue ? initializers[i].call(thisArg, value) : initializers[i].call(thisArg);
	return useValue ? value : void 0;
};
var __esDecorate = function(ctor, descriptorIn, decorators, contextIn, initializers, extraInitializers) {
	function accept(f) {
		if (f !== void 0 && typeof f !== "function") throw new TypeError("Function expected");
		return f;
	}
	var kind = contextIn.kind, key = kind === "getter" ? "get" : kind === "setter" ? "set" : "value";
	var target = !descriptorIn && ctor ? contextIn["static"] ? ctor : ctor.prototype : null;
	var descriptor = descriptorIn || (target ? Object.getOwnPropertyDescriptor(target, contextIn.name) : {});
	var _, done = false;
	for (var i = decorators.length - 1; i >= 0; i--) {
		var context = {};
		for (var p in contextIn) context[p] = p === "access" ? {} : contextIn[p];
		for (var p in contextIn.access) context.access[p] = contextIn.access[p];
		context.addInitializer = function(f) {
			if (done) throw new TypeError("Cannot add initializers after decoration has completed");
			extraInitializers.push(accept(f || null));
		};
		var result = (0, decorators[i])(kind === "accessor" ? {
			get: descriptor.get,
			set: descriptor.set
		} : descriptor[key], context);
		if (kind === "accessor") {
			if (result === void 0) continue;
			if (result === null || typeof result !== "object") throw new TypeError("Object expected");
			if (_ = accept(result.get)) descriptor.get = _;
			if (_ = accept(result.set)) descriptor.set = _;
			if (_ = accept(result.init)) initializers.unshift(_);
		} else if (_ = accept(result)) if (kind === "field") initializers.unshift(_);
		else descriptor[key] = _;
	}
	if (target) Object.defineProperty(target, contextIn.name, descriptor);
	done = true;
};
let PluginRegistryProbe = (() => {
	let _classSuper = TypertRemoteService;
	let _instanceExtraInitializers = [];
	let _fastest_decorators;
	return class PluginRegistryProbe extends _classSuper {
		static {
			const _metadata = typeof Symbol === "function" && Symbol.metadata ? Object.create(_classSuper[Symbol.metadata] ?? null) : void 0;
			_fastest_decorators = [Remote];
			__esDecorate(this, null, _fastest_decorators, {
				kind: "method",
				name: "fastest",
				static: false,
				private: false,
				access: {
					has: (obj) => "fastest" in obj,
					get: (obj) => obj.fastest
				},
				metadata: _metadata
			}, null, _instanceExtraInitializers);
			if (_metadata) Object.defineProperty(this, Symbol.metadata, {
				enumerable: true,
				configurable: true,
				writable: true,
				value: _metadata
			});
		}
		config = __runInitializers(this, _instanceExtraInitializers);
		static Config = z.object({
			registryProbeEnabled: z.boolean().default(true),
			registryProbeTimeoutMs: z.natural().min(1).max(MAX_TIMER_DELAY_MS).default(1500),
			registryProbeCacheTtlMs: z.natural().default(3e5)
		});
		lifetime = new AbortController();
		pending;
		cached;
		constructor(ctx, config) {
			super(ctx, "pluginRegistryProbe");
			this.config = config;
			ctx.effect(() => async () => {
				this.lifetime.abort();
				await this.pending;
			});
		}
		/**
		* Race npm and npmmirror HTTPS ping responses through the Host's fetch proxy.
		* Concurrent readers share a probe; a winner cancels and awaits the other request.
		* @returns the first registry with a successful response, or null when disabled or neither responds successfully; results are cached.
		* @throws rejects when the service has been unloaded.
		*/
		async fastest() {
			this.lifetime.signal.throwIfAborted();
			if (!this.config.registryProbeEnabled) return null;
			if (this.cached !== void 0 && this.cached.expiresAt > Date.now()) return this.cached.registry;
			this.pending ??= this.probe().finally(() => {
				this.pending = void 0;
			});
			return this.pending;
		}
		async probe() {
			const finished = new AbortController();
			const signal = AbortSignal.any([
				this.lifetime.signal,
				finished.signal,
				AbortSignal.timeout(this.config.registryProbeTimeoutMs)
			]);
			const requests = ["https://registry.npmjs.org/-/ping", "https://registry.npmmirror.com/-/ping"].map(async (endpoint) => ({
				registry: new URL("/", endpoint).href,
				response: await fetch(endpoint, {
					signal,
					redirect: "error"
				})
			}));
			const successful = requests.map(async (request) => {
				const { registry, response } = await request;
				if (!response.ok) throw new Error(`Registry ping returned HTTP ${response.status}`);
				return registry;
			});
			let registry;
			try {
				registry = await Promise.any(successful);
			} catch (_unavailableRegistries) {
				registry = null;
			} finally {
				finished.abort();
				const responses = await Promise.allSettled(requests);
				await Promise.allSettled(responses.map(async (result) => {
					if (result.status === "fulfilled") await result.value.response.body?.cancel();
				}));
			}
			if (!this.lifetime.signal.aborted) this.cached = {
				registry,
				expiresAt: Date.now() + this.config.registryProbeCacheTtlMs
			};
			return registry;
		}
	};
})();
//#endregion
export { PluginRegistryProbe as default };
/* Generated by @deepseek-ai/dsh-typert-generator from FaceModel — do not edit. */
import { z } from 'zod'

import { createTypertRemoteInfo } from '@deepseek-ai/dsh-typert-protocol/remote-info'

let _deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema$value
const _deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema = () => (_deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema$value ??= z.union([z.literal(null), z.string()]))

const $remote = createTypertRemoteInfo({
  package: '@deepseek-ai/dsh-client-ui-plugin-manager',
  methods: {
    'pluginRegistryProbe/fastest': {
      service: 'pluginRegistryProbe',
      description: 'Race npm and npmmirror HTTPS ping responses through the Host\'s fetch proxy. Concurrent readers share a probe; a winner cancels and awaits the other request.',
      invocation: { kind: 'direct' },
      parameters: [
      ],
      result: {
        mode: 'strict',
        typeSymbol: '@deepseek-ai/dsh-client-ui-plugin-manager#pluginRegistryProbe/fastest:result',
        create: _deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema,
        description: 'the first registry with a successful response, or null when disabled or neither responds successfully; results are cached.',
        jsonSchema: {"oneOf":[{"type":"null","const":null},{"type":"string"}]},
      },
      sourceLocation: {"file":"packages/client/ui-plugin-manager/src/index.ts","line":51,"column":9},
    },
  },
}, z)

export const TYPERT = {
  package: '@deepseek-ai/dsh-client-ui-plugin-manager',
  face: 'host',
  schemas: [
  ],
  get invocations() { return $remote.descriptors },
  model: {
    "services": [
      {
        "description": "Compares public registry responses on the Host; the Client owns the initial selection.",
        "summary": "Compares public registry responses on the Host; the Client owns the initial selection.",
        "tags": [],
        "jsDoc": "/** Compares public registry responses on the Host; the Client owns the initial selection. */",
        "key": "pluginRegistryProbe",
        "exportName": "default",
        "members": [
          {
            "kind": "method",
            "name": "fastest",
            "signature": "@Remote async fastest(): Promise<string | null>",
            "summary": "Race npm and npmmirror HTTPS ping responses through the Host's fetch proxy.",
            "jsDoc": "/**\n * Race npm and npmmirror HTTPS ping responses through the Host's fetch proxy.\n * Concurrent readers share a probe; a winner cancels and awaits the other request.\n * @returns the first registry with a successful response, or null when disabled or neither responds successfully; results are cached.\n * @throws rejects when the service has been unloaded.\n */"
          }
        ],
        "types": []
      }
    ],
    "events": [],
    "objects": []
  },
}
/* Generated by @deepseek-ai/dsh-typert-generator from the Host FaceModel — do not edit. */
import { z } from 'zod'

import { createTypertRemoteInfo } from '@deepseek-ai/dsh-typert-protocol/remote-info'

let _deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema$value
const _deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema = () => (_deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema$value ??= z.union([z.literal(null), z.string()]))

export const TYPERT_REMOTE = createTypertRemoteInfo({
  package: '@deepseek-ai/dsh-client-ui-plugin-manager',
  methods: {
    'pluginRegistryProbe/fastest': {
      service: 'pluginRegistryProbe',
      description: 'Race npm and npmmirror HTTPS ping responses through the Host\'s fetch proxy. Concurrent readers share a probe; a winner cancels and awaits the other request.',
      invocation: { kind: 'direct' },
      parameters: [
      ],
      result: {
        mode: 'strict',
        typeSymbol: '@deepseek-ai/dsh-client-ui-plugin-manager#pluginRegistryProbe/fastest:result',
        create: _deepseek_ai_dsh_client_ui_plugin_manager_pluginRegistryProbe_fastest_result$schema,
        description: 'the first registry with a successful response, or null when disabled or neither responds successfully; results are cached.',
        jsonSchema: {"oneOf":[{"type":"null","const":null},{"type":"string"}]},
      },
      sourceLocation: {"file":"packages/client/ui-plugin-manager/src/index.ts","line":51,"column":9},
    },
  },
}, z)

export default TYPERT_REMOTE
{
  "meta": {
    "title": "ui-plugin-manager"
  }
}
{
  "meta": {
    "title": "插件管理界面",
    "description": "查看和安装插件包，并进行启用、停用和重试等操作。"
  }
}
{
  "name": "@deepseek-ai/dsh-client-ui-plugin-manager",
  "description": "Plugin management for the dsh web client: the sidebar Plugins panel installs, enables, disables, retries, and composes installed plugin packages",
  "version": "0.2.1-rc.2",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/deepseek-ai/deepseek-harness.git",
    "directory": "packages/client/ui-plugin-manager"
  },
  "type": "module",
  "main": "lib/index.js",
  "types": "lib/types/index.d.ts",
  "exports": {
    ".": {
      "types": "./lib/types/index.d.ts",
      "default": "./lib/index.js"
    },
    "./client": {
      "types": "./lib/types/client/index.d.ts",
      "default": "./lib/client.js"
    },
    "./src/*": "./src/*",
    "./package.json": "./package.json",
    "./typert": {
      "types": "./lib/typert.host.d.ts",
      "default": "./lib/typert.host.js"
    },
    "./remote": {
      "types": "./lib/typert.remote-client.d.ts",
      "default": "./lib/typert.remote-client.js"
    },
    "./locale/*.json": "./locale/*.json"
  },
  "dsh": {
    "client": {
      "inject": [
        "@deepseek-ai/dsh-api-remotes",
        "@deepseek-ai/dsh-client-locale",
        "@deepseek-ai/dsh-client-ui-layout",
        "@deepseek-ai/dsh-client-ui-sidebar"
      ],
      "platform": "web"
    }
  },
  "license": "MIT",
  "peerDependencies": {
    "@deepseek-ai/cordis": "~4.0.5"
  },
  "devDependencies": {
    "@deepseek-ai/cordis": "~4.0.5",
    "@deepseek-ai/dsh-api-remotes": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-locale": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-store": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-test-runtime": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-ui-layout": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-ui-primitives": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-ui-renderer": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-ui-sidebar": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-ui-slots": "0.2.1-rc.2",
    "@deepseek-ai/dsh-package-manifest": "0.2.1-rc.2",
    "@testing-library/react": "^16.3.3",
    "clsx": "^2.1.1",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@deepseek-ai/dsh-util-crypto": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-ui-settings": "0.2.1-rc.2",
    "@deepseek-ai/dsh-plugin-manager": "0.2.1-rc.2",
    "@deepseek-ai/dsh-client-product-analytics": "0.2.1-rc.2"
  },
  "files": [
    "locale/*.json",
    "lib/index.js",
    "lib/client.js",
    "lib/types/**/*.d.ts",
    "lib/typert.host.js",
    "lib/typert.host.d.ts",
    "lib/typert.remote-client.js",
    "lib/typert.remote-client.d.ts"
  ],
  "dependencies": {
    "@deepseek-ai/dsh-timeout": "0.2.1-rc.2",
    "@deepseek-ai/schemastery": "~3.18.5",
    "zod": "4.4.3",
    "@deepseek-ai/dsh-typert-protocol": "0.2.1-rc.2"
  }
}MIT License

Copyright (c) 2026 DeepSeek

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
# Bilingual-pair consistency record for README.md (docs/i18n/README.md): per heading
# section, a hash of its English and Chinese blocks outside code blocks and generated regions.
# After editing either side, bring the other along and re-record with:
#   pnpm run verify-translation-pairing --write packages/client/ui-plugin-market/README.md
/:
  en: af3fe4b70bddbc1b
  zh: ac1c4326165266d9
/deepseek-ai-dsh-client-ui-plugin-market:
  en: 62972eb0dff8c145
  zh: 682cc03b492cd730
/deepseek-ai-dsh-client-ui-plugin-market/summary:
  en: f95719fc57b4e921
  zh: bf8a63b54127c147
/deepseek-ai-dsh-client-ui-plugin-market/table-of-contents:
  en: 76368b6b1da79c80
  zh: 52384aee991ac542
/deepseek-ai-dsh-client-ui-plugin-market/use-this-package:
  en: 2690b95e156cc473
  zh: 0d9e897ad628f9dd
/deepseek-ai-dsh-client-ui-plugin-market/understand-the-implementation:
  en: c56790cb58083f85
  zh: a3d4ad4bad08e483
/deepseek-ai-dsh-client-ui-plugin-market/model-experience:
  en: 08d25ab9cbdd7567
  zh: 26e6e75c123951ee
/deepseek-ai-dsh-client-ui-plugin-market/model-experience/kv-cache-effect:
  en: 4f0eadf94828e66e
  zh: 4f8a6ec170ebbfb6
/deepseek-ai-dsh-client-ui-plugin-market/known-limitations-and-deferred-work:
  en: 5e98bb00293c12e3
  zh: 279b09a42c515d17
/deepseek-ai-dsh-client-ui-plugin-market/known-limitations-and-deferred-work/dev-note:
  en: e67f633dc6fe7773
  zh: 3bb0c20c93f16f98
---
description: "Web 插件页的「发现」标签页：搜索已配置的插件市场索引，查看条目并安装。"
kind: "package-reference"
---

# @deepseek-ai/dsh-client-ui-plugin-market

[English](README.md) | 中文

## 概述

「发现」是**插件**页的第二个标签页，位于**已安装**之后。它列出插件市场索引提供的组合包（bundle）；用户可以管理索引源、在插件市场之间切换、搜索、按分类和标签筛选、排序、打开条目页面，并在确认后安装条目。Host 的 [`pluginMarket`](../../boot/plugin-market/README.zh.md) 服务负责获取和校验索引；本包只负责展示。

## 目录

- [使用本包](#use-this-package)
- [理解实现](#understand-the-implementation)
- [模型体验](#model-experience)
- [已知限制与延期工作](#known-limitations-and-deferred-work)
- [开发备注](#dev-note)

-----

<a id="use-this-package"></a>
## 使用本包

打开**插件**并选择**发现**。没有索引源时，该标签页显示空状态，其中的**添加索引源**按钮打开**索引源**对话框。对话框按插件市场标题列出每个索引源（首次读取前按主机名），并显示其 URL、最近一次读取失败的错误和删除按钮，同时保留一条提示，说明索引由第三方提供。URL 被拒绝时保留草稿并说明原因：不支持的协议、包含凭据或片段、URL 已在列表中，或当前部署无法保存索引源。新添加的索引源成为所选插件市场。

工具栏包含：插件市场菜单，用于切换插件市场，最后一项为**管理索引源…**；搜索框；插件市场声明了标签时显示的**标签**菜单，以勾选标记支持多选；**排序**菜单；以及刷新按钮。插件市场声明了分类时，其后显示分类按钮，**全部**排在第一位。

每张卡片显示图标、本地化标题、标签、一行描述，以及默认版本、作者和发布日期，并只有一个操作：可安装的条目显示**安装**；没有默认版本、且最高版本既不兼容也未豁免的条目显示禁用的**安装**，其提示框说明没有与当前运行的 DSH 兼容的版本；其余条目显示**已安装**、**有新版本**或**随 DSH 提供**，点击后切换到「已安装」标签页，并在该标签页列出该组合包时打开其页面。选择卡片会打开条目页面，显示其完整描述、兼容性提示和默认版本的信息：作者；主页和源代码仓库（在新标签页中打开的链接，仓库旁显示包所在目录）；npm 包和注册表，或 Git 仓库、完整提交和目录；发布日期；分类；标签；以及插件市场。其后是按 SemVer 降序排列的**版本**列表；每行标出推荐、预发布、已安装、不兼容和已豁免的版本，并为安装检查接受的其他版本提供**安装**，DSH 随附的组合包除外。页面的返回链接回到列表，搜索、筛选和排序保持不变。

**安装**选择默认版本并打开确认对话框，显示条目的图标、标题、该版本、作者、来源信息、适用时的豁免提示，以及信任提示。确认后，插件页的安装对话框以该条目的精确 spec 和注册表在检查界面打开；不显示 spec 表单，被拒绝时提供**重试**。条目指定的注册表只用于这一次安装。

Host 的 [`pluginMarket.search`](../../boot/plugin-market/README.zh.md#use-this-package) 负责匹配、过滤、排序和分页；标签页在停止输入 250 毫秒后发送搜索文本。搜索模糊匹配名称、作者、关键词，以及标题、描述、分类和标签的所有语言。所选标签必须全部匹配。有搜索文本时，**排序**提供**最佳匹配**，此外还提供**默认顺序**、**发布时间**以及每个已声明的排序键，排序键以其声明的方向开始；有方向的排序会额外显示一行，用于反转方向。输入文本会把**默认顺序**切换为**最佳匹配**，清空文本时切换回来。分类、标签和排序键按本地化标题列出。列表加载 50 个条目，每次点击**显示更多**再增加 50 个。

读取插件市场时显示卡片骨架屏。读取失败时显示一句简短说明和**重试**，Host 给出的原因显示在**索引源**中对应索引源的下方，并保留该插件市场上一次的列表；读取索引源列表失败时，在该标签页的位置显示**重试**。「发现」在收到 `plugin-market/changed` 和连接重置时重新读取索引源，在收到 `plugin-manager/changed` 时重新计算安装状态。

-----

<a id="understand-the-implementation"></a>
## 理解实现

本插件把标签为**发现**的 `discover` 条目注册到 `plugins.tab`，即 [`ui-plugin-manager`](../ui-plugin-manager/README.zh.md) 声明的标签页 slot；owner props 提供 `install({ spec, registry?, title, version })` 和 `openPackage(name)`；发现页传入条目的本地化标题和所选版本。一个不依赖 React 的控制器在快照存储中拥有索引源读取、索引源编辑，以及所选索引的查询和已加载的页；选择另一个插件市场时从初始查询开始。之后的页发送第一页的 `fetchedAt`，来自已替换文档的页会让列表重新加载一次；再次被替换时读取失败。列表保留其结果所回答的查询，因此新查询加载期间或失败后，空状态文案仍与显示的结果一致；**重试**重新执行失败的读取：某个查询的前几页，或下一页。profile 的组合包变化时，重新加载所有已加载的页以刷新安装状态；索引不再声明的过滤条件或排序键会从查询中移除。尚未发送的搜索文本、打开的条目和确认对话框是组件状态。`presentation.ts` 中的纯函数根据文本得出查询顺序、移除未声明的 id、使用当前界面语言的 `Intl.Collator` 对声明排序，以及列出来源信息。图标以 `referrerpolicy="no-referrer"` 延迟加载，失败时回退到默认插画。

-----

<a id="model-experience"></a>
## 模型体验

无，本包在浏览器中渲染 Host 数据，不向模型请求添加任何内容。

#### KV Cache 影响

无。

## 已知限制与延期工作

<a id="known-limitations-and-deferred-work"></a>

- **没有升级操作**——可用更新只显示为状态。
- **远程图标**——URL 图标由浏览器请求，会向图片主机暴露用户的 IP 地址。Web UI 通过 HTTPS 提供时，浏览器会拦截或升级来自 `http:` 索引的 `http:` 图标，加载失败的图标显示默认插画。

<a id="dev-note"></a>
### 开发备注

<details>
<summary>维护者的工作上下文——点击展开</summary>

无。

</details>
window.__ModuleLoader__.load({
	id: "@deepseek-ai/dsh-client-ui-plugin-market",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
		let react_jsx_runtime = require("react/jsx-runtime");
		let react = require("react");
		let _deepseek_ai_dsh_client_ui_primitives = require("@deepseek-ai/dsh-client-ui-primitives");
		let _deepseek_ai_dsh_client_store = require("@deepseek-ai/dsh-client-store");
		//#region lib/types/client/presentation.js
		/** The query a newly selected index starts with. */
		const INITIAL_QUERY = {
			text: "",
			category: null,
			labels: [],
			sort: { kind: "index" }
		};
		/**
		* Replace the query text. Index order becomes relevance order when blank text gains words, and returns when the text
		* becomes blank; an order chosen while text is present stays.
		* @param query - the current query.
		* @param text - the new text.
		* @returns the query with the text and its order.
		*/
		function withText(query, text) {
			const [was, blank] = [query.text.trim() === "", text.trim() === ""];
			const sort = was && !blank && query.sort.kind === "index" ? { kind: "relevance" } : blank && query.sort.kind === "relevance" ? { kind: "index" } : query.sort;
			return {
				...query,
				text,
				sort
			};
		}
		/**
		* Drop filters and the sort key the index no longer declares, so every active choice stays visible in the toolbar.
		* @param query - the current query.
		* @param metadata - the declarations of the index that answered it.
		* @returns the query itself when every id is declared, otherwise a reduced copy.
		*/
		function declaredQuery(query, metadata) {
			const category = query.category !== null && !Object.hasOwn(metadata.categories, query.category) ? null : query.category;
			const labels = query.labels.filter((label) => Object.hasOwn(metadata.labels, label));
			const sort = query.sort.kind === "key" && !Object.hasOwn(metadata.sortKeys, query.sort.id) ? { kind: "index" } : query.sort;
			return category === query.category && labels.length === query.labels.length && sort === query.sort ? query : {
				...query,
				category,
				labels,
				sort
			};
		}
		/**
		* Order declarations by their localized title, then by id code points.
		* @param declarations - id → declaration with a `title`.
		* @param resolveText - current-language text resolution.
		* @param language - current UI language for collation.
		* @returns declarations in display order.
		*/
		function displayDeclarations(declarations, resolveText, language) {
			const collator = new Intl.Collator(language);
			return Object.entries(declarations).map(([id, declaration]) => ({
				id,
				title: resolveText(declaration.title),
				declaration
			})).sort((a, b) => collator.compare(a.title, b.title) || (a.id < b.id ? -1 : 1));
		}
		/**
		* The version an entry presents and installs by default: its default version, or its highest version when none is compatible.
		* @param entry - the market entry.
		* @returns the presented version.
		*/
		function presentedVersion(entry) {
			return entry.versions.find((version) => version.version === entry.defaultVersion) ?? entry.versions[0];
		}
		/**
		* List where a version installs from, so users can check its origin before installing.
		* @param name - the entry's package name.
		* @param version - the version to install.
		* @returns the npm package and registry, or the repository, full commit, and package directory.
		*/
		function sourceFacts(name, version) {
			const { source } = version;
			if (source.type === "npm") return [{
				kind: "package",
				value: `${name}@${version.version}`
			}, ...source.registry === void 0 ? [] : [{
				kind: "registry",
				value: source.registry
			}]];
			return [
				{
					kind: "repository",
					value: source.url
				},
				{
					kind: "commit",
					value: source.commit
				},
				...source.path === void 0 ? [] : [{
					kind: "directory",
					value: source.path
				}]
			];
		}
		/**
		* Name an index source: its market title once read, otherwise its host.
		* @param index - the configured source.
		* @param resolveText - current-language text resolution.
		* @returns the display name; a URL the browser cannot parse is shown as written.
		*/
		function indexLabel(index, resolveText) {
			if (index.title !== void 0) return resolveText(index.title);
			return URL.canParse(index.url) ? new URL(index.url).host : index.url;
		}
		//#endregion
		//#region \0dsh-css:/home/runner/work/deepseek-harness/deepseek-harness/packages/client/ui-plugin-market/src/client/DiscoverSection.module.css.mjs
		const css = ".dq5LxG_section{flex-direction:column;gap:16px;display:flex}.dq5LxG_toolbar{align-items:center;gap:8px;display:flex}.dq5LxG_marketButton{max-width:240px;margin-left:-8px;font-weight:500}.dq5LxG_marketName{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.dq5LxG_search{flex:1;min-width:120px}.dq5LxG_categories{flex-wrap:wrap;align-items:center;gap:6px;display:flex}.dq5LxG_muted,.dq5LxG_meta{color:var(--dsw-alias-label-tertiary);margin:0;font-size:13px;line-height:20px}.dq5LxG_meta{overflow-wrap:anywhere;font-size:12px;line-height:18px}.dq5LxG_strong{overflow-wrap:anywhere;font-size:14px;font-weight:500;line-height:20px}.dq5LxG_error{color:var(--dsw-alias-state-error-primary);align-items:center;gap:6px;margin:0;font-size:13px;line-height:20px;display:inline-flex}.dq5LxG_failure{align-items:center;gap:10px;display:flex}.dq5LxG_notice{border-radius:var(--dsw-radius-md);background:var(--dsw-alias-state-warn-tertiary);color:var(--dsw-alias-label-secondary);align-items:flex-start;gap:8px;margin:0;padding:10px 12px;font-size:12px;line-height:18px;display:flex}.dq5LxG_notice>svg{color:var(--dsw-alias-state-warn-primary);flex:none;margin-top:2px}.dq5LxG_cards{flex-direction:column;gap:2px;margin:0;padding:0;list-style:none;display:flex}.dq5LxG_card{border-radius:var(--dsw-radius-xl);align-items:center;gap:14px;margin:0 -8px;padding:8px;display:flex;position:relative}.dq5LxG_card:hover{background:var(--dsw-alias-interactive-bg-hover)}.dq5LxG_icon{border:.5px solid var(--dsw-alias-border-l3);border-radius:var(--dsw-radius-lg);width:48px;height:48px;color:var(--dsw-alias-label-secondary);flex:none;justify-content:center;align-items:center;display:inline-flex}.dq5LxG_image{object-fit:contain}.dq5LxG_main{flex-direction:column;flex:1;gap:2px;min-width:0;display:flex}.dq5LxG_titleRow{flex-wrap:wrap;align-items:center;gap:8px;min-width:0;display:flex}.dq5LxG_cardOpen{max-width:100%;color:inherit;font:inherit;text-align:left;cursor:pointer;text-overflow:ellipsis;white-space:nowrap;background:0 0;border:0;padding:0;font-size:14px;font-weight:500;line-height:20px;overflow:hidden}.dq5LxG_cardOpen:after{content:\"\";border-radius:var(--dsw-radius-xl);position:absolute;inset:0}.dq5LxG_cardOpen:focus-visible{outline:none}.dq5LxG_cardOpen:focus-visible:after{outline:var(--dsw-focus-ring-width) solid var(--dsw-focus-ring-color,var(--dsw-alias-state-business-primary));outline-offset:2px}.dq5LxG_description{color:var(--dsw-alias-label-tertiary);-webkit-line-clamp:1;-webkit-box-orient:vertical;font-size:13px;line-height:18px;display:-webkit-box;overflow:hidden}.dq5LxG_cardEnd{z-index:1;flex:none;align-items:center;gap:8px;display:inline-flex;position:relative}.dq5LxG_blocked{opacity:.5;cursor:not-allowed}.dq5LxG_more{align-self:center}.dq5LxG_empty{text-align:center;flex-direction:column;align-items:center;gap:8px;padding:64px 0;display:flex}.dq5LxG_emptyTitle{margin:8px 0 0;font-size:14px;font-weight:500;line-height:20px}.dq5LxG_empty>button{margin-top:8px}.dq5LxG_detail{flex-direction:column;gap:16px;display:flex}.dq5LxG_crumb{color:var(--dsw-alias-label-tertiary);font:inherit;cursor:pointer;background:0 0;border:0;align-self:flex-start;align-items:center;gap:6px;padding:0;font-size:12.5px;display:inline-flex}.dq5LxG_crumb:hover{color:var(--dsw-alias-label-primary)}.dq5LxG_crumb:focus-visible{outline:var(--dsw-focus-ring-width) solid var(--dsw-focus-ring-color,var(--dsw-alias-state-business-primary));outline-offset:2px}.dq5LxG_crumbIcon{transform:rotate(90deg)}.dq5LxG_detailHead{align-items:center;gap:14px;display:flex}.dq5LxG_detailTitle{margin:0;font-size:20px;font-weight:500;line-height:28px}.dq5LxG_detailDescription{color:var(--dsw-alias-label-secondary);overflow-wrap:anywhere;margin:0;font-size:14px;line-height:22px}.dq5LxG_detailSection{flex-direction:column;gap:12px;margin-top:16px;display:flex}.dq5LxG_sectionTitle{margin:0;font-size:14px;font-weight:500;line-height:20px}.dq5LxG_facts{margin:0}.dq5LxG_facts div{border-bottom:.5px solid var(--dsw-alias-border-l2);justify-content:space-between;align-items:center;gap:16px;min-height:44px;padding:8px 2px;display:flex}.dq5LxG_facts dt{color:var(--dsw-alias-label-secondary);flex:none;font-size:13px;line-height:20px}.dq5LxG_facts dd{text-align:end;overflow-wrap:anywhere;min-width:0;margin:0;font-size:13px;line-height:20px}.dq5LxG_facts code{background:var(--dsw-alias-bg-module-platform);box-decoration-break:clone;font-family:var(--ds-font-family-code);border-radius:4px;padding:2px 6px;font-size:12px}.dq5LxG_tags{flex-wrap:wrap;justify-content:flex-end;gap:6px;display:flex}.dq5LxG_dialog{width:min(480px,100vw - 32px)}.dq5LxG_dialogBody{flex-direction:column;gap:12px;display:flex}.dq5LxG_sourceList,.dq5LxG_versions{flex-direction:column;margin:0;padding:0;list-style:none;display:flex}.dq5LxG_sourceRow,.dq5LxG_versionRow{border-bottom:.5px solid var(--dsw-alias-border-l2);align-items:center;gap:8px;padding:8px 0;display:flex}.dq5LxG_sourceError{color:var(--dsw-alias-state-error-primary);overflow-wrap:anywhere;font-size:12px;line-height:18px}.dq5LxG_sourceForm{align-items:center;gap:8px;display:flex}.dq5LxG_grow{flex:1;min-width:0}.dq5LxG_confirmHead{align-items:center;gap:14px;display:flex}.dq5LxG_skeletonFill{background:var(--dsw-alias-bg-skeleton);animation:2s cubic-bezier(.36,0,.64,1) infinite dq5LxG_dsh-market-skeleton}.dq5LxG_icon.dq5LxG_skeletonFill{border-color:#0000}.dq5LxG_skeletonBar{border-radius:var(--dsw-radius-xs);height:12px;margin:4px 0;display:block}.dq5LxG_skeletonTitle{width:min(144px,60%)}.dq5LxG_skeletonDescription{width:min(280px,85%)}@keyframes dq5LxG_dsh-market-skeleton{0%{opacity:1}40%{opacity:.6}80%,to{opacity:1}}@media (prefers-reduced-motion:reduce){.dq5LxG_skeletonFill{animation:none}}.dq5LxG_link{color:var(--dsw-alias-link);overflow-wrap:anywhere;text-decoration:none}.dq5LxG_link:hover{text-decoration:underline}";
		const tagId = "@deepseek-ai/dsh-client-ui-plugin-market/DiscoverSection.module.css";
		if (typeof document !== "undefined" && document.querySelector("style[data-plugin-css=" + JSON.stringify(tagId) + "]") === null) {
			const tag = document.createElement("style");
			tag.dataset.plugin = "@deepseek-ai/dsh-client-ui-plugin-market";
			tag.dataset.pluginCss = tagId;
			tag.textContent = css;
			document.head.appendChild(tag);
		}
		var DiscoverSection_module_css_default = {
			"blocked": "dq5LxG_blocked",
			"card": "dq5LxG_card",
			"cardEnd": "dq5LxG_cardEnd",
			"cardOpen": "dq5LxG_cardOpen",
			"cards": "dq5LxG_cards",
			"categories": "dq5LxG_categories",
			"confirmHead": "dq5LxG_confirmHead",
			"crumb": "dq5LxG_crumb",
			"crumbIcon": "dq5LxG_crumbIcon",
			"description": "dq5LxG_description",
			"detail": "dq5LxG_detail",
			"detailDescription": "dq5LxG_detailDescription",
			"detailHead": "dq5LxG_detailHead",
			"detailSection": "dq5LxG_detailSection",
			"detailTitle": "dq5LxG_detailTitle",
			"dialog": "dq5LxG_dialog",
			"dialogBody": "dq5LxG_dialogBody",
			"dsh-market-skeleton": "dq5LxG_dsh-market-skeleton",
			"empty": "dq5LxG_empty",
			"emptyTitle": "dq5LxG_emptyTitle",
			"error": "dq5LxG_error",
			"facts": "dq5LxG_facts",
			"failure": "dq5LxG_failure",
			"grow": "dq5LxG_grow",
			"icon": "dq5LxG_icon",
			"image": "dq5LxG_image",
			"link": "dq5LxG_link",
			"main": "dq5LxG_main",
			"marketButton": "dq5LxG_marketButton",
			"marketName": "dq5LxG_marketName",
			"meta": "dq5LxG_meta",
			"more": "dq5LxG_more",
			"muted": "dq5LxG_muted",
			"notice": "dq5LxG_notice",
			"search": "dq5LxG_search",
			"section": "dq5LxG_section",
			"sectionTitle": "dq5LxG_sectionTitle",
			"skeletonBar": "dq5LxG_skeletonBar",
			"skeletonDescription": "dq5LxG_skeletonDescription",
			"skeletonFill": "dq5LxG_skeletonFill",
			"skeletonTitle": "dq5LxG_skeletonTitle",
			"sourceError": "dq5LxG_sourceError",
			"sourceForm": "dq5LxG_sourceForm",
			"sourceList": "dq5LxG_sourceList",
			"sourceRow": "dq5LxG_sourceRow",
			"strong": "dq5LxG_strong",
			"tags": "dq5LxG_tags",
			"titleRow": "dq5LxG_titleRow",
			"toolbar": "dq5LxG_toolbar",
			"versionRow": "dq5LxG_versionRow",
			"versions": "dq5LxG_versions"
		};
		//#endregion
		//#region lib/types/client/DiscoverSection.js
		/** Discover: search one plugin market index, read an entry's page, and install a version. */
		/** Typing pause before the query text is sent. */
		const TEXT_DELAY_MS = 250;
		/** Artwork size inside the 48px icon frame, as on the Installed tab. */
		const ICON = 36;
		const FAILURE_KEYS = {
			fetch: "readFailed",
			invalid: "readInvalid",
			changed: "readChanged"
		};
		const FACT_KEYS = {
			package: "factPackage",
			registry: "factRegistry",
			repository: "factRepository",
			commit: "factCommit",
			directory: "factDirectory"
		};
		function MarketIcon({ src, size }) {
			const [failed, setFailed] = (0, react.useState)();
			return src === void 0 || src === failed ? (0, react_jsx_runtime.jsx)(_deepseek_ai_dsh_client_ui_primitives.PluginArtworkDefault, { size }) : (0, react_jsx_runtime.jsx)("img", {
				className: DiscoverSection_module_css_default.image,
				src,
				widt