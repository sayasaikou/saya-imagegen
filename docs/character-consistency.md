# 角色一致性：方案排名、显存账与选型

> 目标：让 AI 生成的人物跟参考立绘一致。硬件基准：单卡 16 GB 显存 / 32 GB 内存。

## 一、先给结论

| 需求 | 首选 | 代价 |
| --- | --- | --- |
| **1:1 复刻立绘** | 专用角色 LoRA（Anima 2B / SDXL 谱系 / FLUX.1） | 15–40 张同角色图，单卡可训 |
| **换场景/姿势还认得出** | Qwen-Image-Edit 系（零样本） | 1–3 张参考图，20B 级需 int8 或 GGUF |
| **只换画风** | Krea 2 style reference | 只迁移风格，不保身份 |
| **最小最好跑** | FLUX.2 klein 9B KV | 4 步，像度比 Qwen 低一档 |

**一句话**：要「一模一样」只能上 LoRA；要「认得出」用参考图编辑；两者不要混着期待。

## 二、零样本方案排名（16 GB 可落地）

| 名次 | 方案 | 像不像 | 16 GB | 说明 |
| --- | --- | --- | --- | --- |
| 1 | Qwen-Image-Edit-2511 / 2.1（int8 或 GGUF Q4） | 最强一档 | 能跑，慢，需 offload | 官方模型卡明确「角色一致性显著提升」；1–3 张参考最优；支持「人物+场景」 |
| 2 | FLUX.2 klein 9B KV | 中上 | 最舒服 | 原生 ReferenceLatent 多图，4 步，fp8 约 9–10 GB |
| 3 | Z-Image-Turbo 6B | 只能靠 LoRA | 很舒服 | 官方点名适配 16 GB；但**不支持参考图** |
| 4 | Krea 2 Turbo + style reference | 只有风格 | 舒服 | 官方模板确认它做的是风格参考，不是同一张脸 |
| 5 | IP-Adapter / FaceID / InstantID / PuLID | 老一代 | SDXL 可以 | 全部停在 2024–2025；没有 Qwen 版本；要装第三方节点 |

## 三、关键链路与参数

### Qwen-Image-Edit（零样本首选）

```
UNETLoader(qwen_image_edit_2511_int8_convrot)
CLIPLoader(qwen_2.5_vl_7b_fp8_scaled, qwen_image)
VAELoader(qwen_image_vae)
ModelSamplingAuraFlow(shift=3.1)
FluxKontextMultiReferenceLatentMethod(index_timestep_zero) ×2  ← 正/负条件各一
LoadImage(参考图) → FluxKontextImageScale → TextEncodeQwenImageEditPlus（image1..image3 三个槽）
LoadImage(底图) → FluxKontextImageScale → VAEEncode → KSampler.latent
CFGNorm(1.0)
KSampler: euler / simple / denoise 1.0
  常规档 40 步 / cfg 4.0；Lightning 档 4 步 / cfg 1.0
```

三个硬坑：

1. 用 int8 / 第三方重打包权重时，**必须加 `FluxKontextMultiReferenceLatentMethod`**，否则参考图等于没接。
2. 参考图先过 `FluxKontextImageScale`；尺寸差太多会漂。
3. `denoise 1.0` 时场景图不保留像素，只当内容参考。想要构图/背景一模一样，要么降 denoise 到 0.5–0.8（身份保真会掉），要么先做 ControlNet 深度/线稿锁构图。

提示词范式：

```
Keep the character and pose in <image2> unchanged, place the character into the scene of <image1>,
preserve facial features, hair color, hairstyle and outfit; match the lighting and perspective of <image1>.
```

### FLUX.2 klein 9B KV（最轻）

```
UNETLoader(flux-2-klein-9b-kv-fp8) + CLIPLoader(qwen_3_8b_fp8mixed, flux2) + VAELoader(flux2-vae)
LoadImage ×N → ImageScaleToTotalPixels(lanczos, 1MP) → VAEEncode → ReferenceLatent（每张一条）
FluxKVCache
CLIPTextEncode（提示词用 Figure 1 / Figure 2 指代）
CFGGuider(1) + Flux2Scheduler(steps=4) + KSamplerSelect(euler) + SamplerCustomAdvanced
```

### 两段式：先出场景，再编辑进角色

```
第一段：Z-Image-Turbo（8 步）或 Krea 2（8 步）出场景
第二段：Qwen-Image-Edit 把角色放进去（image1 = 场景，image2 = 角色）
```

这是官方「person + scene」多图参考的标准用法。

## 四、显存与训练账

| 项 | 数字 |
| --- | --- |
| Qwen-Image-Edit-2511 int8 权重 | 约 20 GB（20B 级），16 GB 要 offload 或换 GGUF Q4（约 12 GB） |
| Qwen-Image-Edit-2511 bf16 | 约 40 GB，16 GB 不用想 |
| FLUX.2 klein 9B fp8 | 约 9–10 GB（文本编码器可分段加载） |
| Krea 2 Turbo int8 | 约 12.6 GB + 文本编码器 2.5 GB，16 GB 能跑 |
| Anima 2B | 约 3.9 GB，极舒适 |
| SDXL 二次元底模 | 约 6.5 GB，极舒适 |

训练侧（官方示例档位）：

- ai-toolkit 的 Qwen-Image LoRA 官方示例要 **24 GB**，Qwen-Image-Edit 要 **32 GB** ⇒ 16 GB 不建议。
- sd-scripts 的 FLUX.1 官方支持 16 GB（`--blocks_to_swap`）。
- Anima 2B 有 `anima_train_network.py`，`--blocks_to_swap` 可按变体调。
- Krea 2 训练卡的不是显存：24.5 GB 的 bf16 权重 + 量化，32 GB 内存在加载阶段就会见底。

**结论**：16 GB + 32 GB 内存能训的是 Anima(2B) / SDXL 谱系 / FLUX.1；20B 级编辑模型只适合推理（int8/GGUF），不适合训练。

## 五、IP-Adapter 家族现状（不要作为新项目起点）

| 方案 | SDXL | FLUX.1 | Qwen-Image | 最后动静 |
| --- | --- | --- | --- | --- |
| IP-Adapter（原版） | ✓ | ✗ | ✗ | 2023 |
| ComfyUI_IPAdapter_plus | ✓ | ✗ | ✗ | 2025-04 作者宣布维护模式 |
| IP-Adapter FaceID | ✓ | ✗ | ✗ | 2024 |
| InstantID | ✓ | ✗ | ✗ | 2024-07 后无 release |
| PuLID v1.1 | ✓ | ✗ | ✗ | 2024-10-31 |
| PuLID-FLUX v0.9.1 | ✗ | ✓ | ✗ | 2024-10-31 |
| Qwen 原生编辑 | — | — | ✓ | 现役 |

2026 年的新项目基本不再用它们；ComfyUI 核心节点里也没有 IP-Adapter，走这条路要装第三方节点。

## 六、选型判据

1. 先问「像」到什么程度：1:1 → LoRA；认得出 → 参考图编辑。
2. 再问「要几张图」：角色多、每张只要几次 → 参考图编辑；同一角色反复出 → LoRA。
3. 最后看显存：16 GB 下 20B 编辑模型必须 int8/GGUF + offload，速度按分钟计。
4. **不要用「换背景」需求去测身份参考模型**：背景崩不代表身份不行，但会把你引向错误的模型选型。
