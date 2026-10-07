# Anime Wallpaper Upscaler

![左侧为普通放大，右侧为官方 Real-ESRGAN NCNN/Vulkan 4x 超分的同一张动漫图片](docs/assets/promotion/anime-4x-comparison.png)

## 暂停喜欢的一帧，把它留在桌面。

**番剧截图一键超分，自动生成适配当前屏幕、保留完整构图的高清 Windows 壁纸。** 完成首次
安装后，把截图拖到桌面快捷方式，选择 2x/3x/4x；工作流会在本机自动检测物理屏幕和 Vulkan GPU。

- 支持 Windows 10/11；新增 macOS 命令行与 Terminal 入口（Apple Silicon／Intel 运行时）
- 全程本地处理，不上传截图
- 使用官方 Real-ESRGAN NCNN/Vulkan 推理
- 默认保留完整构图，不悄悄裁掉边缘内容

[English](README.md)

## macOS 安装

使用含此次适配的源码分支；现有 Windows 发布 ZIP 尚不包含 macOS 支持。
先安装 Python 3.10 或更新版本，再双击 `install.command`，或在 Terminal 执行：

```bash
./install.command
.venv/bin/python scripts/upscale_wallpaper.py --input "/图片路径/image.png" --scale 4
```

安装器会先展示上游条款并请求确认，再下载约 52 MB 的官方 macOS 通用运行时，校验
压缩包及每个安装文件，创建项目内 `.venv`，并可选注册 Codex skill 符号链接。已有 skill
目录或链接会保留。运行时包含原生 arm64／x86_64 程序，通过自带 MoltenVK 使用 Metal；
无需 CUDA、PyTorch、Homebrew 或额外 GPU 驱动。首次编译着色器可能较慢。

Terminal 入口为 `./scripts/run-wallpaper.command "/图片或文件夹路径"`，会询问一次
2／3／4 倍；双击入口会询问输入路径。macOS 入口不创建 Windows 的拖放桌面快捷方式。
两平台共用命令行参数、批处理、对比图、保留构图和 `--copy-desktop`。
`--target auto` 检测主显示器物理分辨率，支持 Retina；也可用 `--target 2560x1664`
手动指定。结果默认在 Finder 打开，可用 `--no-open-output` 关闭。

无人值守安装需先阅读 [第三方声明](THIRD_PARTY_NOTICES.md)，再传
`--accept-upstream-license`；`--skip-skill` 跳过 skill 注册。已有官方 ZIP 可用
`--archive /路径/realesrgan-ncnn-vulkan-20220424-macos.zip`，仍执行相同校验。
若 macOS 拦截经过校验的程序，在“系统设置 → 隐私与安全性”允许该程序；保持 Gatekeeper
开启。[本机验证记录](docs/macos-verification.md)。

## 从番剧截图到桌面壁纸

### 查看 4x 局部细节差异

![普通放大的 K-ON 截图与经验证的 Real-ESRGAN 4x 结果对比](docs/assets/promotion/k-on-detail-comparison-4x.png)

### 查看 2560x1600 Windows 桌面实测

![上方为原截图直接设为壁纸，下方为 Real-ESRGAN 4x 保留构图壁纸](docs/assets/promotion/k-on-desktop-comparison.png)

示例来自同一次本地记录：721x406 截图、官方 `realesrgan-x4plus-anime`、4x、`preserve`
模式、2560x1600 目标，以及 NVIDIA GeForce RTX 5070 Ti Laptop GPU。
[运行证据](docs/release/evidence/k-on-promotion-run.json) ·
[宣传素材声明](docs/assets/promotion/NOTICE.md)

## 三步开始

1. 从 [Releases](https://github.com/zc4578980-tech/anime-wallpaper-upscaler/releases/latest) 下载并解压最新版 Windows ZIP。
2. 双击 `install.cmd`，阅读上游条款并确认下载经过校验的官方运行时。
3. 把截图或文件夹拖到生成的桌面快捷方式，选择 2x、3x 或 4x。

不需要手动安装模型。真正执行推理的是 Real-ESRGAN 和 ncnn；本仓库提供 Windows 壁纸工作
流，不宣称原创模型。超分不能保证恢复源截图中不存在的全部细节。

## 本项目与官方 Real-ESRGAN 的区别

| 能力 | 官方 Real-ESRGAN / NCNN-Vulkan | 本项目 |
| --- | --- | --- |
| 超分推理与模型 | 提供算法、模型和 Vulkan 可执行程序 | 下载并调用官方发行版，不宣称原创算法或模型 |
| 完整构图壁纸 | 输出原始超分结果 | `preserve` 模式保留完整原图构图 |
| 适配物理屏幕 | 需要自行指定尺寸或后处理 | 自动检测主显示器物理分辨率，并保留手动覆盖 |
| 画面比例不一致 | 不负责壁纸构图 | 用同图的柔化模糊副本填充空余区域，前景不裁切 |
| 批量壁纸 | 上游程序有自己的文件/文件夹输入方式 | 增加多输入、递归、单图失败隔离和汇总日志 |
| 对比图 | 官方可执行程序不生成 | 默认自动生成可重复的细节前后对比图 |
| Windows 上手流程 | 提供程序与上游说明 | 增加校验安装、本地 Python 环境、拖放、快捷方式和修复指引 |
| Agent / 自然语言调用 | 直接提供命令行参数 | 把自然语言壁纸需求映射为文档化的封装参数 |

真正执行超分的是上游项目。本仓库的独立价值，是围绕上游推理整理出的 Windows 壁纸工作流。

## Agent Skill（进阶）

完成安装后，Agent 可以把自然语言需求转换成与命令行完全相同、可复现的本地封装命令。例如：

- “把 `C:\Pictures\wallpaper.png` 放大 3 倍，适配当前屏幕，并保留完整构图。”
- “批量处理 `C:\Pictures\Anime` 及其所有子文件夹中的壁纸，使用 2 倍。”
- “使用 Vulkan GPU 0，把所有 4 倍结果放到 `D:\Wallpaper Output`。”
- 只有明确接受损失边缘内容时，才说“裁切并铺满屏幕”。

安装器会把本仓库注册为：

```text
%USERPROFILE%\.codex\skills\anime-wallpaper-upscale -> 仓库根目录
```

Agent 会把需求落实为明确参数，再调用封装脚本。例如：

```powershell
.\.venv\Scripts\python.exe .\scripts\upscale_wallpaper.py `
  --input "C:\Pictures\wallpaper.png" `
  --scale 3 `
  --target auto `
  --gpu auto `
  --mode preserve
```

Agent 不会替代或重新实现推理：

```text
用户意图 -> Agent Skill -> 壁纸封装脚本
         -> 官方 realesrgan-ncnn-vulkan.exe
         -> 官方模型 / ncnn / Vulkan
```

## 环境要求

- 64 位 Windows 10/11，PowerShell 5.1 或更高版本。
- 为获得最简单的首次安装体验，建议系统有 Windows Package Manager（`winget`）。缺少 Python
  时，安装器会在用户确认后用 winget 为当前用户安装官方 Python 3.12。
- 也可以预先安装 64 位 Python 3.10 或更高版本。
- 支持 Vulkan 的 GPU，以及较新的 NVIDIA、AMD 或 Intel 驱动。
- 足够存放官方程序、模型和输出图片的磁盘空间。

处理完全在本机进行，封装脚本不会上传输入图片，也不会生成式重绘原画。

## 安装

双击 `install.cmd`，或运行上方等价的 PowerShell 命令。安装器会：

1. 下载前展示上游来源和许可证提示；
2. 查找 Python；缺少时，在用户确认后通过 `winget` 按当前用户安装官方 Python 3.12；
3. 创建项目本地 `.venv` 并安装 `requirements.txt`；
4. 把固定版本的官方 Real-ESRGAN Windows 发行包下载到已忽略的 `tools/`；
5. 校验压缩包大小和 SHA-256，并确认可执行程序及固定的 2x/3x/4x 模型全部存在，再原子安装；
6. 安装 Codex skill junction，并创建拖放桌面快捷方式；
7. 运行命令行帮助冒烟测试。

官方可执行程序和全部必需模型由安装器自动从上游下载，绝不会提交到本仓库。普通用户不应
自己下载或移动模型文件。无人值守安装前，请先阅读[第三方声明](THIRD_PARTY_NOTICES.md)，再使用
`-AcceptUpstreamLicense`；只有同时授权为当前用户安装 Python 时才附加 `-InstallPython`。网络
中断时，受控的临时文件保留在 `tools\.downloads`，重新运行安装器可以续传。

### 高级恢复：使用已有官方运行时

这不是普通安装步骤。已经自行维护官方运行时的高级用户，可以把解压目录传给封装脚本：

```powershell
.\.venv\Scripts\python.exe .\scripts\upscale_wallpaper.py `
  --input "C:\Pictures\wallpaper.png" `
  --tool-dir "C:\Tools\realesrgan-ncnn-vulkan-20220424-windows"
```

目录中必须有 `realesrgan-ncnn-vulkan.exe`，以及 `models\` 下与倍率兼容的 `.param` 和 `.bin`
文件。也可以在当前环境中用 `REALESRGAN_TOOL_DIR` 指向同一目录。

## 命令行

一次处理多个文件和一个文件夹：

```powershell
.\.venv\Scripts\python.exe .\scripts\upscale_wallpaper.py `
  --input "C:\Pictures\one.png" `
  --input "C:\Pictures\two.jpg" `
  --input "C:\Pictures\Wallpaper Folder" `
  --recursive `
  --scale 3 `
  --target auto `
  --gpu auto `
  --mode preserve
```

`--input` 接受 JPG、JPEG、PNG、WebP 或文件夹，可重复使用。文件夹默认只扫描顶层；加上
`--recursive` 后扫描子目录。重复路径只处理一次。

| 参数 | 含义与默认值 |
| --- | --- |
| `--input PATH` | 必填图片或文件夹；多输入时重复书写 |
| `--recursive` | 包含文件夹子目录中的支持格式图片 |
| `--scale {2,3,4}` | 上游超分倍率；默认 `4` |
| `--target auto\|WIDTHxHEIGHT` | 默认检测物理主屏；也可传入 `2560x1600` |
| `--gpu auto\|ID` | 探测 Vulkan 设备并默认由 ncnn 选择；可用输出中的数字 ID 覆盖 |
| `--model MODEL` | 覆盖按倍率自动选择的上游模型 |
| `--mode {preserve,cover}` | 默认 `preserve`；`cover` 会裁切以铺满屏幕 |
| `--out-dir PATH` | 把整批结果放到指定目录 |
| `--tool-dir PATH` | 高级覆盖：使用已有的官方运行时目录 |
| `--copy-desktop` | 额外复制每张成品壁纸到当前用户桌面 |
| `--compare-full-input` | 对比完整输入，而不是默认细节区域 |
| `--x-bias 0..1` / `--y-bias 0..1` | 调整 `cover` 裁切位置；默认 `0.5` |
| `--no-compare` | 不生成前后对比图 |
| `--no-upscaled-source` | 壁纸生成后删除原始超分 PNG |
| `--no-open-output` | 完成后不自动打开成功输出目录 |

`--target auto` 使用支持 DPI 感知的 Windows API。检测失败时会明确警告，临时使用
`2560x1600`，并提示如何手动覆盖。GPU 探测会列出官方程序报告的 Vulkan 设备；
`--gpu auto` 把最终设备选择交给 ncnn。

## 模式与输出

- `preserve`：完整图片居中，空余屏幕区域用同图的暗化模糊副本填充；这是默认模式。
- `cover`：通过裁切铺满屏幕；仅在可以舍弃边缘内容时使用。

没有 `--out-dir` 时，单个文件的结果放到同目录的 `Wallpaper Upscaler Output`，文件夹批量
结果放到该文件夹内部的同名输出目录。递归任务会保留相对子目录结构。每个成功项目通常生成：

- `<名称>_realesrgan_<倍率>x.png`：官方运行时的原始输出；
- `<名称>_wallpaper_AI_<宽>x<高>_<模式>_<倍率>x.jpg`：最终壁纸；
- `<名称>_AI_compare_<倍率>x.jpg`：细节对比图。

每个输出根目录都有 `anime-wallpaper-upscaler.log`，记录成功/失败数量和逐项结果。单张坏图
不会中止其余批次；部分失败返回退出码 `1`，安装或输入错误返回 `2`。

## 故障修复

| 现象 | 处理方法 |
| --- | --- |
| 找不到 Python，或版本低于 3.10 | 双击 `install.cmd` 并确认按当前用户安装 Python；若没有 `winget`，从 [python.org](https://www.python.org/downloads/windows/) 安装 64 位 Python、勾选 **Add python.exe to PATH**，再重跑 `install.cmd` |
| 下载中断或网络失败 | 检查是否能访问 GitHub Releases，再重跑 `install.cmd`；受校验约束的部分下载会保留以便续传 |
| 缺少可执行程序或模型 | 直接启动快捷方式或重跑 `install.cmd`；安装器会自动恢复固定的官方程序和模型 |
| 未发现 Vulkan GPU / Vulkan 初始化失败 | 更新 [NVIDIA](https://www.nvidia.com/Download/index.aspx)、[AMD](https://www.amd.com/en/support/download/drivers.html) 或 [Intel](https://www.intel.com/content/www/us/en/download-center/home.html) 驱动后重试 |
| 手动 GPU ID 被拒绝 | 查看命令输出的设备列表，传入其中的数字 ID，或改用 `--gpu auto` |
| 图片损坏或格式不受支持 | 重新导出为有效的 JPG、JPEG、PNG 或 WebP，再运行批次 |

## 重建视觉素材

仓库用脚本保证视觉素材可重复生成，不依赖手工拼图。项目自有 demo 的重建命令是：

```powershell
python .\scripts\build_original_demo.py `
  --output ".\docs\assets\demo-source-original.png"

python .\scripts\build_demo_assets.py `
  --source ".\docs\assets\demo-source-original.png" `
  --upscaled "C:\Demo\original_realesrgan_4x.png" `
  --wallpaper "C:\Demo\original_wallpaper.jpg" `
  --overview ".\docs\assets\workflow-overview.jpg" `
  --social-preview ".\Wallpaper Upscaler Output\demo-social-preview.jpg"
```

仓库自带源图是带四种彩色边角标记的项目原创技术场景。三联图中的每个面板都会完整
contain-fit，不裁切内容。

当前宣传预览由两张已选对比素材重建：

```powershell
python .\scripts\build_promotion_assets.py `
  --detail ".\docs\assets\promotion\k-on-detail-comparison-4x.png" `
  --desktop-comparison ".\docs\assets\promotion\k-on-desktop-comparison.png" `
  --output ".\docs\assets\social-preview.jpg"
```

K-ON! 示例不是项目自有 MIT 素材；复用或发布前请阅读
[宣传素材声明](docs/assets/promotion/NOTICE.md)。替换素材时仍应只使用自己创作或明确获准
再分发的原图。

## 上游署名与许可证

本项目是基于 [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)、
[Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan) 和
[ncnn](https://github.com/Tencent/ncnn) 的集成封装。推理代码、模型、可执行程序及相关组件继续
适用各自的上游许可证，详见[第三方声明](THIRD_PARTY_NOTICES.md)。

MIT 许可证适用于本仓库自己的封装代码、文档，以及[演示素材声明](docs/assets/NOTICE.md)中列出的
原创演示资产。这不会重新许可、删除或弱化上游推理代码、模型、可执行程序及依赖各自适用的
许可证、声明和署名。
