###############################################################################
# 03_Interactive_CRF/dprime_crf.R
# 对标 JS computeCRF_dprime() + zScore() → d' = z(HR) - z(FAR)
#
# 信号检测论辨别力指数 d' 的 CRF 分析:
#   - Hit:  Matching 试次中按了"匹配键" → P(respond "match" | trial is Matching)
#   - FA:   NonMatching 试次中按了"匹配键" → P(respond "match" | trial is NonMatching)
#   - d' = qnorm(HR) - qnorm(FAR), 使用 log-linear 校正
#
# 生成:
#   1. 全数据聚合 d' CRF (Self vs Stranger)
#   2. 按组聚合 d' CRF
#   3. d' SPE 差异图 (d'_Self - d'_Stranger)
#   4. d' + P(Match) + ACC 三指标对比图
###############################################################################

# ===========================================================================
# 0. 初始化
# ===========================================================================
source(file.path("shared", "utils.R"), chdir = TRUE)
OUT_DIR <- file.path(R_VERSION_DIR, "03_Interactive_CRF", "outputs")
dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)

cat("=== 03_Interactive_CRF: d' CRF Analysis ===\n")

# ===========================================================================
# 1. 加载数据 (与 interactive_crf.R 相同逻辑)
# ===========================================================================
cat("Loading all raw data...\n")
all_data <- load_all_data()

if ("stage" %in% names(all_data)) {
  formal <- all_data[grepl("test", all_data$stage, ignore.case = TRUE), ]
} else {
  formal <- all_data
}

# Matching / NonMatching 判定
formal$Matching <- ifelse(
  formal$CorrectKey == formal$Response,
  "Matching", "NonMatching"
)

# Identity 判定
formal$Identity <- ifelse(
  grepl("self", tolower(formal$Label)), "Self",
  ifelse(grepl("stranger", tolower(formal$Label)), "Stranger", "Unknown")
)

# RT 列统一到毫秒
formal$RT_ms <- as.numeric(formal$RT)
formal <- formal[!is.na(formal$RT_ms) & formal$RT_ms > 0 & formal$RT_ms < 5000, ]

cat("Formal trials:", nrow(formal), "\n")
cat("Unique subjects:", length(unique(formal$subjectID)), "\n")

# ===========================================================================
# 2. 全数据聚合 d' CRF
# ===========================================================================
cat("\n--- Computing d' CRF (Self vs Stranger, Aggregated) ---\n")

dprime_self_all   <- compute_crf_dprime(formal[formal$Identity == "Self",    ], n_quantiles = 5)
dprime_strang_all <- compute_crf_dprime(formal[formal$Identity == "Stranger", ], n_quantiles = 5)

if (nrow(dprime_self_all) == 0 || nrow(dprime_strang_all) == 0) {
  cat("ERROR: Insufficient data for d' CRF calculation.\n")
  cat("  Self d' bins:", nrow(dprime_self_all), "\n")
  cat("  Stranger d' bins:", nrow(dprime_strang_all), "\n")
  quit(save = "no", status = 1)
}

dprime_agg <- bind_rows(
  data.frame(dprime_self_all,   Identity = "Self",    stringsAsFactors = FALSE),
  data.frame(dprime_strang_all, Identity = "Stranger", stringsAsFactors = FALSE)
)

cat("d' CRF data rows:", nrow(dprime_agg), "\n")

# ===========================================================================
# 3. d' CRF 绘图函数
# ===========================================================================
plot_dprime_crf <- function(bins, title_str, subtitle_str = NULL) {
  p <- ggplot(bins, aes(x = rtMean, y = dprime, color = Identity, fill = Identity)) +
    geom_line(linewidth = 1.2) +
    geom_point(size = 2.5) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "grey60", linewidth = 0.5) +
    scale_color_manual(values = c("Self" = "#ff9800", "Stranger" = "#2196f3")) +
    scale_fill_manual(values = c("Self" = "#ff9800", "Stranger" = "#2196f3")) +
    scale_x_continuous(name = "RT (ms)") +
    scale_y_continuous(name = expression("d' (辨别力指数)")) +
    labs(title = title_str, subtitle = subtitle_str) +
    theme_spe()
  p
}

# 全数据聚合 d' CRF
p_dprime_agg <- plot_dprime_crf(
  dprime_agg,
  "d' CRF — Self vs Stranger (Aggregated)",
  paste0("d' = z(HR) - z(FAR) | n = ", nrow(formal), " trials")
)
save_plot_png(p_dprime_agg, file.path(OUT_DIR, "CRF_dprime_Aggregated.png"))

# ===========================================================================
# 4. d' SPE 差异图 (d'_Self - d'_Stranger)
# ===========================================================================
cat("\n--- Generating d' SPE Difference ---\n")

if (nrow(dprime_self_all) >= 2 && nrow(dprime_strang_all) >= 2) {
  dprime_spe <- data.frame(
    rtMean = dprime_self_all$rtMean,
    dprime_diff = dprime_self_all$dprime - dprime_strang_all$dprime,
    stringsAsFactors = FALSE
  )

  p_dprime_spe <- ggplot(dprime_spe, aes(x = rtMean, y = dprime_diff)) +
    geom_line(color = "#e91e63", linewidth = 1.5) +
    geom_point(color = "#e91e63", size = 3) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "grey50") +
    labs(
      title = expression("SPE d' = d'"["Self"] * " - d'"["Stranger"]),
      subtitle = paste0("Aggregated across all subjects | n = ", nrow(formal), " trials"),
      x = "RT (ms)",
      y = expression(Delta * " d'")
    ) +
    theme_spe()
  save_plot_png(p_dprime_spe, file.path(OUT_DIR, "CRF_dprime_SPE_Difference.png"))

  # 合并图: d' CRF + d' SPE
  p_combined_dprime <- cowplot::plot_grid(
    p_dprime_agg, p_dprime_spe,
    ncol = 1, rel_heights = c(1, 0.8)
  )
  save_plot_png(p_combined_dprime, file.path(OUT_DIR, "CRF_dprime_Combined.png"), height = 8)
}

# ===========================================================================
# 5. 按组聚合 d' CRF
# ===========================================================================
cat("\n--- Generating Group-Specific d' CRF ---\n")

group_dprime_list <- list()
for (g in sort(unique(formal$groupID))) {
  gdata <- formal[formal$groupID == g, ]
  if (nrow(gdata) < 40) next  # d' 需要更多试次

  self_dp   <- compute_crf_dprime(gdata[gdata$Identity == "Self",    ], n_quantiles = 5)
  strang_dp <- compute_crf_dprime(gdata[gdata$Identity == "Stranger", ], n_quantiles = 5)
  if (nrow(self_dp) < 2 || nrow(strang_dp) < 2) next

  g_parts <- list()
  if (nrow(self_dp) > 0) {
    g_parts[[length(g_parts) + 1]] <- data.frame(
      self_dp, Identity = "Self", stringsAsFactors = FALSE
    )
  }
  if (nrow(strang_dp) > 0) {
    g_parts[[length(g_parts) + 1]] <- data.frame(
      strang_dp, Identity = "Stranger", stringsAsFactors = FALSE
    )
  }
  if (length(g_parts) == 0) next
  g_bins <- bind_rows(g_parts)
  g_bins$Group <- g
  group_dprime_list[[as.character(g)]] <- g_bins
}

if (length(group_dprime_list) > 0) {
  dprime_by_group <- bind_rows(group_dprime_list)

  p_group_dprime <- ggplot(dprime_by_group, aes(x = rtMean, y = dprime, color = Identity)) +
    geom_line(linewidth = 0.8) +
    geom_point(size = 1.5) +
    facet_wrap(~ Group, ncol = 4) +
    scale_color_manual(values = c("Self" = "#ff9800", "Stranger" = "#2196f3")) +
    geom_hline(yintercept = 0, linetype = "dashed", color = "grey60", linewidth = 0.3) +
    labs(title = "d' CRF by Group", x = "RT (ms)", y = "d'") +
    theme_spe(base_size = 9)
  save_plot_png(p_group_dprime, file.path(OUT_DIR, "CRF_dprime_By_Group.png"),
                width = 14, height = 10)
}

# ===========================================================================
# 6. 三指标对比: d' vs P(Match) vs ACC
# ===========================================================================
cat("\n--- Generating d' vs P(Match) vs ACC Comparison ---\n")

# P(Match) 模式
crf_self_pm   <- compute_crf_bins(formal, identity_sel = "Self",    n_quantiles = 5, y_mode = "pMatch")
crf_strang_pm <- compute_crf_bins(formal, identity_sel = "Stranger", n_quantiles = 5, y_mode = "pMatch")

# ACC 模式
crf_self_acc   <- compute_crf_bins(formal, identity_sel = "Self",    n_quantiles = 5, y_mode = "acc")
crf_strang_acc <- compute_crf_bins(formal, identity_sel = "Stranger", n_quantiles = 5, y_mode = "acc")

# d' 模式 (已有 dprime_self_all, dprime_strang_all)

# 统一 x 轴为 rtMean (ms)
make_comparison_df <- function(self_bins, strang_bins, metric_name) {
  if (nrow(self_bins) == 0 || nrow(strang_bins) == 0) return(data.frame())
  bind_rows(
    data.frame(rtMean = self_bins$x,   value = self_bins$y,   Identity = "Self",    Metric = metric_name, stringsAsFactors = FALSE),
    data.frame(rtMean = strang_bins$x, value = strang_bins$y, Identity = "Stranger", Metric = metric_name, stringsAsFactors = FALSE)
  )
}

df_pm   <- make_comparison_df(crf_self_pm,   crf_strang_pm,   "P(Match)")
df_acc  <- make_comparison_df(crf_self_acc,  crf_strang_acc,  "ACC")
df_dp   <- bind_rows(
  data.frame(rtMean = dprime_self_all$rtMean,   value = dprime_self_all$dprime,   Identity = "Self",    Metric = "d'", stringsAsFactors = FALSE),
  data.frame(rtMean = dprime_strang_all$rtMean, value = dprime_strang_all$dprime, Identity = "Stranger", Metric = "d'", stringsAsFactors = FALSE)
)

comp_all <- bind_rows(df_pm, df_acc, df_dp)

p_comparison <- ggplot(comp_all, aes(x = rtMean, y = value, color = Identity)) +
  geom_line(linewidth = 1.0) +
  geom_point(size = 2.0) +
  facet_wrap(~ Metric, ncol = 1, scales = "free_y",
             strip.position = "left") +
  scale_color_manual(values = c("Self" = "#ff9800", "Stranger" = "#2196f3")) +
  labs(
    title = "CRF / CAF / d' — Three Metrics Comparison",
    subtitle = paste0("All groups aggregated | n = ", nrow(formal), " trials"),
    x = "RT (ms)", y = NULL
  ) +
  theme_spe(base_size = 10) +
  theme(strip.placement = "outside", strip.background = element_rect(fill = "grey95"))
save_plot_png(p_comparison, file.path(OUT_DIR, "CRF_Three_Metrics_Comparison.png"),
              width = 10, height = 12)

cat("\n=== d' CRF Analysis DONE ===\n")
cat("Outputs saved to:", OUT_DIR, "\n")
