# Krea 2 提示词与提质量：六条路，哪条真有用

> 官方源：仓库 `inference.py`、`docs/prompting.md`、`docs/expansion.txt`、ComfyUI 教程。以下「官方」与「实测」分开标。

## 一、三条提示词硬规矩（官方）

1. **用自然语言成句，不要堆 Danbooru tag。**
2. **长而详细的提示词效果最好**，但也吃很短的一句。
3. **要画面里出现文字，就用引号把那个词包起来。**

官方 16 个示例几乎每条都写全六个维度：介质/技法、光、构图/镜头、色彩、景深/虚实、叙事/负空间。

⚠️ **关键区别**：官方的 `shallow depth of field` 都带明确作用对象（`on hand`、`on the animal's face`）。写一句光禿禿的景深词，模型会把整张画都糊掉——实测崩过四张。

## 二、一个关键认知修正：Turbo 是关闭 CFG 的

官方 `inference.py` 默认 `--steps 28 --cfg 4.5`，但 Turbo 示例是：

```
--steps 8 --cfg 0.0 --mu 1.15 --width 2048 --height 2048
```

参数说明写着 `--cfg (0 disables CFG)`。

**结论**：Turbo 是 guidance-free 的蒸馏模型。两个直接后果：

1. **负向提示词在 Turbo 上基本无效**（没有 CFG 就没有负向分支）。
2. ComfyUI 里 `cfg=1.0` ≈ 官方 `cfg=0`。「cfg 1.0 很平」不是没调好，是这就是 Turbo 的正常样子。

本机那些「cfg 2.0 细节暴增」的现象，本质是给一个不需要 CFG 的模型强加 CFG：细节是加出来了，但容易过锐、过脏。

需要真正的负向，要上 NAG（Normalized Attention Guidance）或 NegPiP 类节点。

## 三、六条提质量途径（按性价比）

| # | 途径 | 收益 | 成本 | 评价 |
| --- | --- | --- | --- | --- |
| 1 | 分辨率上 2K | 立竿见影 | 20 s → 85–143 s | 已验证，性价比第一 |
| 2 | 提示词扩写（expansion.txt） | 补齐六维度 | 接一个 LLM | 值得，但要人工过一眼防加戏 |
| 3 | RAW + 52 步 | **不是提清晰，是提多样性** | 权重 12 GB + 6 倍时间 | 适合训 LoRA 与两阶段采样，不适合为了画质单跑 |
| 4 | style reference | 「要这个味」最直接 | 另下 int8 权重 + LoRA | 有参考图就上 |
| 5 | 官方 style LoRA（9 个） | 立竿见影 | 几十~几百 MB | 是别人的风格 |
| 6 | 精度档 fp8/int8/nvfp4 | 实测无 A/B | — | 16 GB 只有 nvfp4 塞得下 |

## 四、RAW 到底是不是「更清晰的 Turbo」

**不是。** Turbo 是把 52 步蒸馏成 8 步的快速版，两者画质上限相近。RAW 换来的是**多样性**与可塑性，官方明确说它的用途是 fine-tuning / post-training / LoRA 训练。

「换 RAW 就变清晰」是错误预期。但 RAW 确实是两阶段采样的第一阶段好选择：先用 RAW 跑前 N% 步起形，再用 Turbo 收尾。

## 五、两种社区工作流（值得知道，不一定马上装）

- **两阶段采样器**：Stage 1 用 RAW 跑前段（构型好），Stage 2 用 Turbo 类 LoRA 跑余下（快、质量高），支持两个分辨率与 `handoff_percent` 交接点。它同时修了 ComfyUI 的一个问题：非 Turbo 模型的分辨率相关 shift 没设对。
- **高级节点包**（功能更全也更重）：真 diffusers 管线、三阶段渐进高分辨率、NAG 负向、视觉 prompt、原生量化计算（3 MP 时约快 1.45 倍）。先跑通两阶段再考虑。

## 六、可直接抄写的六维模板

```
[介质] 2D anime illustration with physically based rendering feel
[光] top-side backlight, hard-edged cast shadows, strong teal bounce light
[构图] medium close-up, subject slightly off-center, generous negative space on the left
[材质] matte skin with warm translucency; rough leather broad specular; pinpoint metal speculars
[色] teal and orange grading, shadows tinted deep indigo, never pure black
[后期] bloom on highlights, subtle film grain, shallow depth of field on the face
```

## 七、边界

- 以上参数与结论来自单卡 16 GB 环境；换精度档、换卡后需重测。
- 官方文档给的「推荐值」是给大多数人的；本机塞不下 fp8 时，nvfp4 是唯一选择，不代表它更优。
