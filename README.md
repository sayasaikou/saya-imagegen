# saya-imagegen

本地纯 AI 出图（文生图 / 图生图 / 角色一致性）的方法与判据集。

适用于单卡 16 GB 显存、以二次元插画与写实二次元为目标、用 ComfyUI 做后端的场景。不包含模型权重、素材与成品图。

## 这份文档面向谁

- **面向**：已经能跑通 ComfyUI、但发现「出图不难，出到能用很难」的人。这里只留能复核的结论、参数与失败记录。
- **不面向**：照搬。文中的尺寸、步数、cfg、denoise 都是特定环境的一次取值，换硬件、换底模版本后需要重新标定。
- **证据分级**：结论标「实测」（有可复核输出）／「文档」（官方文档或模型卡）／「推断」（由机制推出，未验证）。三档不混写。

## 三条地基

### 1. 质量的分界线在材质与光影，不在分辨率

把图放大到 2K 不会让布料变成布、金属变成金属。真正的差距是：

- 同一光源下，五种材质给出五组不同的高光（皮肤极弱漫反射、头发线状、皮革大面积粗糙、金属极小点高光、橡胶几乎无高光）；
- 皮肤有三层冷暖（暖白亮部 → 交界线高饱和暖红透光带 → 暗部冷青紫，不压黑）；
- 硬边切块阴影 ＋ 背景色反弹光。

细节写法见 [`docs/material-and-lighting.md`](docs/material-and-lighting.md)。

### 2. 一次只改一个变量，同 seed 对比

画风、构图、身份三个变量同时动，出来的图无法归因。所有对比一律固定 seed、尺寸、步数，只改一个参数，并把「改了什么」写在文件名里。

### 3. 画风不能靠堆形容词

实测：在提示词里塞一整段「最高优先级风格约束」，并声明冲突时以它为准 —— 仍不改变画风。风格要么来自底模/风格 LoRA，要么来自参考图，要么来自对物理光色的具体描述。形容词越堆越容易互相冲突。

## 已验证的模型与参数（16 GB 单卡）

| 模型 | 定位 | 典型参数 | 速度 |
| --- | --- | --- | --- |
| SDXL 谱系二次元底模（Illustrious / NoobAI / WAI） | 平涂二次元的标准答案；角色 LoRA 生态最大 | 832×1216，28 步，`dpmpp_2m` / `karras`，cfg 6.5 | 12–18 s / 张 |
| Anima 2B | 新二次元基座，显存极舒适，可训 LoRA | 1024²，8–10 步 | 数秒 |
| Krea 2 Turbo | 审美上限高，偏写实；自然语言提示词 | 1024²，8 步，cfg 1.0 | 约 20 s / 张；1024×1536 约 45 s |
| Z-Image Turbo | 商用许可干净，写实与中英文排版 | 8 步，cfg 1 | 快 |

分辨率与步数只能解决「清不清楚」，解决「像不像那个材质」的还是模型+提示词+参考图。

## 角色一致性：三条路

| 路线 | 像不像 | 成本 | 适用 |
| --- | --- | --- | --- |
| **专用角色 LoRA** | 最像（1:1 复刻） | 15–40 张同角色图，单卡可训 | 长期角色、要反复出图 |
| 参考图编辑（Qwen-Image-Edit 系） | 中上，换场景/姿势仍认得出 | 零训练，1–3 张参考图 | 一次性需求、角色多 |
| 风格参考（Krea 2 style reference） | 只迁移画风，不保身份 | 一张参考图 | 统一画风 |
| Identity Edit（Krea 2 专用 LoRA） | 只会复制源图，不会演绎新姿势 | 低 | 不推荐用于换场景 |

**判据**：要「一模一样」只能上 LoRA；要「换个场景还认得出」用参考图编辑；Identity Edit 是复制工具，不是生成工具。细节见 [`docs/character-consistency.md`](docs/character-consistency.md)。

## 提示词写法（按模型分）

| 模型 | 提示词形式 | 硬约束 |
| --- | --- | --- |
| SDXL 二次元底模 | Danbooru tag（小写、下划线换空格） | 角色/服装 tag 放前面 |
| Krea 2 | 自然语言成句，长描述更好 | 要文字就加引号；`shallow depth of field` 必须带作用对象 |
| Qwen-Image-Edit | 自然语言指令，`<image1>` 引用图 | 用「保持什么 + 改什么」句式 |

三个反复踩的坑：

1. **负向里写目标风格等于把它推远**。想要 3D 渲染感却在负向写 `3d render`，会一直往手绘方向走。
2. **`semi-realistic` 会把人推向真人**。要二次元的脸，必须显式写 `anime facial proportions / large eyes / stylized features`。
3. **`illustration / painterly` 会拉满手绘感**。想要三渲二质感，就不能用这两个词当主锚。

## 失败方案（不要重走）

| 方案 | 结果 | 根因 |
| --- | --- | --- |
| 用 Identity Edit 换背景 | 背景崩、人物像贴上去 | 整条链没有 mask，全程全图重采样；它本质是复制源图 latent |
| 跨模型低 denoise 重绘 | denoise 0.30–0.40 结构可保，0.50 直接换头 | 模型不认识该角色，denoise 一高就按自己的先验重画脸 |
| 提示词堆「最高优先级风格段」 | 画风不变 | 风格不是提示词能单独决定的；位置/体量/形式也可能违反官方规范 |
| 负向写 `no flat colour blocks` 之类 | 无效 | CFG-distilled 模型整条链路没有负向分支 |
| 一次改多个参数找「最优解」 | 无法归因 | 画风、身份、构图互相干扰 |

## 文档

| 文档 | 内容 |
| --- | --- |
| [`docs/experiment-log.md`](docs/experiment-log.md) | 实验记录索引：做过什么、参数、结论、待复跑清单 |
| [`docs/material-and-lighting.md`](docs/material-and-lighting.md) | 材质与光影拆解（皮肤三层、五种高光、青橙） |
| [`docs/krea2-prompting.md`](docs/krea2-prompting.md) | Krea 2 提示词规范与六条提质量路线 |
| [`docs/krea2-style-tuning.md`](docs/krea2-style-tuning.md) | 画风调校七个方向与三渲二开关 |
| [`docs/krea2-identity-edit.md`](docs/krea2-identity-edit.md) | Identity Edit 实测与边界 |
| [`docs/character-consistency.md`](docs/character-consistency.md) | 角色一致性方案排名、显存账、链路口径 |
| [`docs/model-landscape.md`](docs/model-landscape.md) | 16 GB 模型选型与许可 |
| [`docs/community-notes.md`](docs/community-notes.md) | 写实二次元社区做法汇编（带冲突点） |
| [`docs/lora-training.md`](docs/lora-training.md) | 角色 LoRA 数据集、配置与验收 |
## 工具

| 文件 | 作用 |
| --- | --- |
| `tools/comfygen.py` | ComfyUI 命令行入口（多底模族、批量、LoRA、hires fix、img2img、ESRGAN） |
| `tools/promptbox.py` | 基于角色档案与场景池的提示词随机生成，用于打破模板化输出 |
| `tools/anima_material_probe.py` | 同 seed 材质对照（基线 vs 细节 LoRA 堆叠） |
| `tools/krea2_style_ref.py` | style reference 多参考图对照，同 prompt 同 seed |

## 许可

MIT。模型权重、LoRA 与素材遵循各自的原始许可，不随仓附带。
