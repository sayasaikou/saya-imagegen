# 写实二次元：社区做法汇编（带筛选）

> 目标风格：2D 画风锚 + 物理光照词 + 材质逐件描述 + 一次 2-pass 放大。少任何一件，画面就会滑向平涂或 3D 渲染。
> 本文只留能指认、能复现的部分；互相矛盾的说法标出冲突点。

## 一、四段拆解（可直接抄的结构）

| 段 | 写什么 | 可用原词 |
| --- | --- | --- |
| 0 质量/触发 | 模型要求的前缀、LoRA 触发词 | `masterpiece, best quality, absurdres`（Illustrious 系）；`newest, very aesthetic`（NoobAI 系） |
| 1 主体段 | 镜头、人数、姿势、构图、角色特征 | `1girl, solo, cowboy shot / upper body / close-up, looking at viewer` |
| 2 材质段 | **逐件**写材质与反光强度 | 皮肤：`detailed skin, skin pores, subsurface scattering`；头发：`detailed hair strands, angel ring`；布料：`matte wool, rough cotton, fabric folds`；金属：`polished metal, sharp specular highlight, small point highlight` |
| 3 光照段 | 主光方向 + 色温 + 环境反弹 + 阴影形态 | `cinematic lighting, rim light, backlight, volumetric light, chiaroscuro, ambient occlusion, warm key light, cool ambient light, environment color bounce` |
| 4 后期段 | 镜头/胶片/调色语言 | `depth of field, film grain, chromatic aberration, high contrast, color graded` |

两个非直觉但有效的细节：

- **加 `nose, lips`**：半写实风 LoRA 作者把这两个词写进正向，用来把「无鼻无唇」的动漫脸推向半写实。
- **`chiaroscuro` 不是所有模型都认**：Flux 与 Illustrious 认识，Pony 不认识。

## 二、最有效的两个旋钮

1. **风格斜率**：正向加 `(realistic, photorealistic)`、负向加 `(anime, anime screenshot, anime coloring)` 往写实走；反过来回二次元。比换模型便宜。
2. **hires fix 的第二遍**：低分辨率出构图 → 放大 → 低 denoise 重绘，材质细节几乎全在这一遍长出来。

## 三、负向清单（哪些词会把画面拉回平涂/塑料）

| 要排除 | 负向词 | 为什么 |
| --- | --- | --- |
| 纯色块阴影 / 赛璐璐 | `flat color, flat shading, cel shading, solid shadows, posterized, two-tone shading` | 这些词在潜空间里就是「平涂分离」那一类画风 |
| 画得太简/太草 | `simple eyes, simple drawing, sketch, lineart only` | 半写实 LoRA 作者的官方负向清单 |
| 塑料皮肤/娃娃感 | `plastic, plastic skin, doll, airbrushed, smooth skin, waxy` | 皮肤滑块 LoRA 的定义就是「-3 = 塑料，+3 = 真实」 |
| 3D 渲染感 | `3d, cgi, render, octane render, unreal engine` | 写实向微调模型官方负向 |
| 动漫味太重（想更写实） | `anime, anime screenshot, anime coloring`（**低权重**） | 减动漫感的常规做法 |
| 糊/低清 | `lowres, blurry, jpeg artifacts, worst quality, low quality` | 通用 |

**两个冲突点**：

1. `chromatic aberration`：一个官方的负向里有它，另一个官方示例把它放正向（追求胶片脏感）。想干净别加，想电影感再加。
2. `anime` 是**滑杆不是开关**：负向权重 0.3–0.5 是「减动漫感」；权重 1.0 以上会把脸型与眼比例一起拉走，反而不像插画。

## 四、参数建议（按模型）

| 模型 | CFG | 步数 | 采样器 | 分辨率 |
| --- | --- | --- | --- | --- |
| Illustrious XL | 5–7.5 | 20–28 | Euler a | 1024² 档 |
| NoobAI XL 1.1 | 5–6 | 25–30 | Euler a | 832×1216 首选（v-prediction，需 `prediction_type=v_prediction` + `rescale_betas_zero_snr=True`） |
| Animagine XL 3.1 | 5–7 | <30 | Euler a | 1024² 与若干 16:9 档 |
| 写实向 SDXL 微调 | 4.0 | 20 | DPM++ SDE Karras | 832×1216 → 1536×2048 |
| SDXL 原生 / 通用 | 5–8（社区惯例） | 25–35 | DPM++ 2M Karras | 1024² 档 |

### 提材质细节的参数技巧（比调 CFG 有用）

1. **hires fix 的 denoise 是材质开关**：`R-ESRGAN 4x+` 放大时 0.2–0.5，Latent 放大时约 0.6。
2. **人脸细节用 0.45**：皮肤滑块 LoRA 作者明确建议；过高会在脸上出奇怪 artifact。
3. **denoise 越高越「脏」**：想要干净皮肤就压 denoise。
4. **CFG 不是越高越好**：写实向微调反而把 CFG 压到 4.0，用低 CFG + 低步数换自然光感。

## 五、工作流要点

### 两段式（必做）

第一遍 1024 档、20–28 步，只写主体+构图+大致光位；第二遍放大 1.5–2× 后以 0.2–0.5 denoise 重绘。细节不是第一遍能长出来的，是放大后有像素预算才长出来的。

### 局部重绘

对脸/手/金属扣/皮革分别打 mask 重绘，denoise 0.35–0.6。全局重绘会把已经对的光影和构图一起改坏。

### ControlNet 分工

- `lineart / softedge / canny`：锁线稿与轮廓，防止写实化把线吃掉；
- 深度图：锁空间与光位。

两边分开管，不要在一条 ControlNet 上挂两种需求。

## 六、六个常见坑

| 坑 | 现象 | 解法 |
| --- | --- | --- |
| 1 | 阴影是大片纯色块，没有渐变 | 加 `soft gradient shadows, ambient occlusion`，负向加 `cel shading, flat shading` |
| 2 | 皮肤像塑料/硅胶 | 正向加 `skin pores, subsurface scattering`；负向加 `plastic, smooth skin, waxy` |
| 3 | 所有材质一个亮度 | 逐件写材质（皮肤/头发/布料/金属分别给高光形态） |
| 4 | 越写越像 3D 渲染，丢手绘感 | 正向保留 `2D illustration, hand-drawn lineart`，负向加 `3d, cgi, render`；hires denoise 别超 0.6 |
| 5 | 拿平涂图去 img2img 转写实，转不动 | 平涂图的线稿与色块会把重绘锁回平涂；直接重出，不要强转 |
| 6 | 放大后人脸出怪纹理/细节糊成一团 | 人脸区域单独 inpaint（denoise 0.35–0.45），不要整图高 denoise 重绘 |

## 七、平台声量（选型的参考，不是依据）

P 站自报模型的数据里，闭源订阅服务（NovelAI 类）大一个量级；开源 SDXL 谱系声量小得多。**这不说明开源不能出好图**，只说明「看别人用什么」不能直接当选型依据。

## 八、本仓对社区做法的取舍

- 抄四段结构与材质词表（可指认、可复验）；
- 不抄「魔法数字」式的步数/cfg（它们随模型版本漂）；
- 冲突的说法一律标出来，不选边。
