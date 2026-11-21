---
description: 对指定文件过安检并给判定
---
对 $ARGUMENTS 执行：
1) security_pipeline.py --file <路径>
2) 若 PASS/WARN，再用 warn_verify.py 定 W0-W4
3) 输出：判定、哈希、命中、可验证等级、下一步
BLOCK 一票否决；WARN 需书面接受；不解释成允许。
