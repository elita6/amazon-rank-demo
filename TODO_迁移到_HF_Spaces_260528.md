# TODO: 迁移 demo 到 Hugging Face Spaces

> 文件: TODO_迁移到_HF_Spaces_260528.md
> 创建日期: 2026-05-28
> 更新日期: 2026-06-03
> 用途: 记录把 Streamlit Cloud demo 迁到 Hugging Face Spaces 的待办与决策，避免 keepalive 长期拉锯
> 状态: 暂缓迁移（2026-06-03 keepalive 升 v4「每 30 分钟」后体验已基本解决；且 HF 免费 Space 据传也会休眠，迁移收益待核实）

## 背景

ElitaFolio 个人网站作品集有一张「Amazon 类目评分系统」卡片，底部「查看在线系统 Demo」
按钮跳转到 Streamlit Cloud 部署的 demo（`https://amazon-rank-demo-elita.streamlit.app/`）。
（注：早期是 iframe 内嵌，2026-06 已改为按钮跳转，不再嵌入。）
免费版无访问会休眠——实测休眠阈值远短于官方曾说的「7 天」，约**数小时**级别；
访客打开会先看到睡眠页 + 等 ~30s 唤醒，体验不好。

历史尝试：
- **v1 (2026-05-16)**: GitHub Actions + Playwright 每 3 天访问一次。
  实际不工作（Streamlit 后来把 app 移进 `/~/+/` iframe，老脚本找不到 `stApp`
  选择器，等不到就静默 success），用户几天后打开还是睡眠页。
- **v2 (2026-05-28)**: 加 stealth + 多策略唤醒按钮 + 等不到就 exit 1。
  失败仍然 silent，因为 ready 检测还是只看主 frame。
- **v3 (2026-05-28)**: 多就绪信号 race + 遍历所有 iframe + 失败 dump artifact。
  当前能正常识别 ready 信号（命中 `frame[.../~/+/]:selector:[data-testid="stApp"]`）。
- **v4 (2026-06-03)**: 发现**真正根因是 cron 频率太低**——v1–v3 一直每天/每 3 天才跑 1 次，
  而 Streamlit 休眠阈值只有数小时，访问间隔 > 阈值必睡，跟选择器/iframe 无关。
  改为 **每 30 分钟**（公开仓库 Actions 免费）+ 加 Playwright 浏览器缓存加快高频运行；脚本逻辑未动。

## 为什么还要迁

v3 治标不治本：

| 风险 | 概率 | 当前防御 |
|---|---|---|
| Streamlit 又改 UI/test-id/iframe 路径 | 中 | 多选择器覆盖一部分，治不了根 |
| Streamlit 加强 bot 检测识破 Playwright | 中 | stealth 撑一段时间 |
| GitHub 60 天无 commit 自动停 cron | 高 | 无 |
| keepalive 失败但用户不查 Actions | 高 | v3 会标红但没通知 |

预计每 3-6 个月会被 Streamlit 改一次。

⚠️ **但迁移的核心前提需重新核实**：原以为「HF Spaces 免费版不休眠、零维护」，但据了解
**HF 免费 Space（CPU basic）现在似乎也会在约 48h 无访问后休眠/暂停**。若属实，迁过去只是把
阈值从「数小时」换成「48 小时」，**照样要保活**，并非零维护，迁移性价比大降。
→ 迁移前务必先确认 HF 最新休眠政策；若 HF 也睡，建议直接留在 Streamlit + v4 保活。

## 迁移步骤（估计 15 分钟）

1. **HF 账号 + 新 Space**
   - 去 https://huggingface.co/new-space
   - SDK 选 Streamlit，Hardware 默认 CPU basic（免费）
   - Space 名称建议 `amazon-rank-demo`，账号 `elita6`（或对应 HF 用户名）

2. **代码迁移**
   - 把 `E:\Study\AI\amazon-rank-demo\streamlit_app\` 内容拷到 HF Space 仓库
   - HF 要求入口文件叫 `app.py`（或在 README.md frontmatter 指定 `app_file`）
   - `requirements.txt` 直接复用
   - `data/` 里的 CSV/JSON 一起带过去
   - HF Space 仓库根目录加 `README.md`，开头 YAML frontmatter（HF 元数据）：
     ```yaml
     ---
     title: Amazon Rank Demo
     emoji: 📊
     colorFrom: blue
     colorTo: purple
     sdk: streamlit
     sdk_version: 1.39.0   # 与 requirements.txt 对齐
     app_file: streamlit_app/main.py   # 按真实入口改
     pinned: false
     ---
     ```

3. **测试 HF 部署**
   - 推上去等 build 完（HF 会自动跑 `pip install` + 启动 streamlit）
   - 打开 `https://huggingface.co/spaces/<用户>/amazon-rank-demo` 确认能正常用
   - 测一次 7-10 天后再访问（或翻 HF 文档确认免费版是否真的不睡）

4. **改网站链接**
   - 网站现在是**按钮跳转**（已无 iframe 内嵌）。在 `E:\Work\cv\ElitaFolio\index.html` 里搜
     `amazon-rank-demo-elita.streamlit.app`，把 `#live-demo-link` 按钮的 href 换成
     HF Space 地址即可（HF 格式: `https://<用户>-amazon-rank-demo.hf.space`）。
   - 顺带去掉/调整只为 Streamlit 服务的预热脚本（DOMContentLoaded 里的 warm 逻辑）和
     「休眠唤醒」提示小字（i18n key `demo.note`）。

5. **HF 跑稳 1 周后清理**
   - 删 `E:\Study\AI\amazon-rank-demo\.github\workflows\keepalive.yml`
   - 删 `E:\Study\AI\amazon-rank-demo\.github\scripts\keepalive.py`
   - Streamlit Cloud 老 demo 可以保留（不占额度）或在控制台手动删
   - 删本 TODO 文件 + 记忆 [[reference-amazon-rank-demo]] 里更新地址

## 备选方案（不迁，凑合用）

如果迁移成本看着太大，最低限度补两个洞：

1. **失败时发飞书消息**: 在 keepalive workflow 加 `if: failure()` 步骤调飞书 webhook
2. **Heartbeat workflow 防 60 天停 cron**: 加一个每月跑一次 push `.heartbeat`
   时间戳文件的 workflow，永远重置 GitHub 60 天计时器

补完之后还是会被 Streamlit 改坑到，但至少能在告警当天去修，不会等到访问网站才发现。

## 决策记录

- **2026-05-28**: 倾向选项 A（迁 HF）但本次先不动，列入待办，有空再做。
  v3 keepalive 已经能跑，短期不紧急。
- **2026-06-03**: keepalive 升 v4（每 30 分钟）+ 网站加休眠提示与悬停预热，体验问题已基本解决；
  同时发现 HF 免费版可能也休眠、迁移不一定免维护 → **暂缓迁移**。
  若要不迁也进一步硬化，优先做下方「备选方案」：Heartbeat 防 60 天停 cron + 失败飞书告警。
  （本次另修复了跨榜联动「流转漏斗」的 matplotlib ImportError，与本 TODO 无关，单独记。）
