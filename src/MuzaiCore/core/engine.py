from ..interfaces.system import IAudioEngine


class AudioEngine(IAudioEngine):

    def load_event_bus(self, event_bus):
        raise NotImplementedError()

    def set_project(self, project):
        """将引擎与一个项目关联。"""
        raise NotImplementedError()

    def play(self):
        """开始播放。"""
        raise NotImplementedError()

    def stop(self):
        """停止播放并回到开头。"""
        raise NotImplementedError()

    def render_next_block(self):
        """
        处理下一个音频数据块。
        这是音频处理的核心循环，通常由音频硬件回调函数驱动。
        在我们的模拟中，我们将手动或在一个模拟线程中调用它。
        """
        raise NotImplementedError()

    def report_latency(self) -> float:
        """
        报告总延迟（以秒为单位）。
        这包括硬件延迟、插件延迟等。
        """
        raise NotImplementedError()
