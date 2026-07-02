import multiprocessing

# CarbonSnap 在 4C / 4G 的课程 VM 上，先保守一点。
# 课程文档给出的 cpu*2+1 对这个项目可能偏大。
workers = min(3, multiprocessing.cpu_count())
timeout = 600
graceful_timeout = 60
accesslog = "-"
errorlog = "-"
capture_output = True
