class Config:
    def __init__(
        self,
        min_length = 1.92,
        window_size = 30,
        n_hop = 512,
        step_size = 10,
        det_threshold = 0.5,
        sample_rate = 8000
    ) -> None:
        self.min_length = min_length
        self.window_size = window_size
        self.step_size = step_size
        self.n_hop = n_hop
        self.det_threshold = det_threshold
        self.sample_rate = sample_rate  

    @staticmethod
    def default():
        return Config()
    
    def single_batch_length(self):
        return self.window_size * self.n_hop