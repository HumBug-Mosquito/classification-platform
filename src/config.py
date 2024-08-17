class Config:
    def __init__(
        self,
        min_length = 1.92,
        window_size = 30,
        n_hop = 512,
        step_size = 10,
        det_threshold = 0.5,
    ) -> None:
        self.min_length = min_length
        self.window_size = window_size
        self.step_size = step_size
        self.n_hop = n_hop
        self.det_threshold = det_threshold

    @staticmethod
    def default():
        return Config()
