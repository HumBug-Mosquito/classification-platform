import logging

import timm
import torch
import torch.nn as nn
import torchaudio.transforms as AT
import torchvision.transforms as VT
from nnAudio import features

logger = logging.getLogger(__name__)

class MidsMEDModel(nn.Module):
    class PCENTransform(nn.Module):

        def __init__(self, eps=1e-6, s=0.025, alpha=0.98, delta=2, r=0.5, trainable=True):
            super().__init__()
            if trainable:
                self.log_s = nn.Parameter(torch.log(torch.Tensor([s])))
                self.log_alpha = nn.Parameter(torch.log(torch.Tensor([alpha])))
                self.log_delta = nn.Parameter(torch.log(torch.Tensor([delta])))
                self.log_r = nn.Parameter(torch.log(torch.Tensor([r])))
            else:
                self.s = s
                self.alpha = alpha
                self.delta = delta
                self.r = r
            self.eps = eps
            self.trainable = trainable


        def pcen(self, x, eps=1e-6, s=0.025, alpha=0.98, delta=2, r=0.5, training=False):
            frames = x.split(1, -2)
            m_frames = []
            last_state = None
            for frame in frames:
                if last_state is None:
                    last_state = s * frame
                    m_frames.append(last_state)
                    continue
                if training:
                    m_frame = ((1 - s) * last_state).add_(s * frame)
                else:
                    m_frame = (1 - s) * last_state + s * frame
                last_state = m_frame
                m_frames.append(m_frame)
            M = torch.cat(m_frames, 1)
            if training:
                pcen_ = (x / (M + eps).pow(alpha) + delta).pow(r) - delta ** r
            else:
                pcen_ = x.div_(M.add_(eps).pow_(alpha)).add_(delta).pow_(r).sub_(delta ** r)
            return pcen_

        def forward(self, x):
    #         x = x.permute((0,2,1)).squeeze(dim=1)
            if self.trainable:
                x = self.pcen(x, self.eps, torch.exp(self.log_s), torch.exp(self.log_alpha), torch.exp(self.log_delta), torch.exp(self.log_r), self.training and self.trainable)
            else:
                x = self.pcen(x, self.eps, self.s, self.alpha, self.delta, self.r, self.training and self.trainable)
    #         x = x.unsqueeze(dim=1).permute((0,1,3,2))
            return x

    def __init__(self):
        super().__init__()
        model_name = 'convnext_base_384_in22ft1k'
        image_size = 384
        # num_classes=0 removes the pretrained head
        self.backbone = timm.create_model(model_name,
                        pretrained=False, num_classes=2, in_chans=1,
                        drop_path_rate=0.1, global_pool='avgmax',
                        drop_rate=0.1)
        #####  This section is model specific
        #### It freezes some fo the layers by name
        #### you'll have to inspect the model to see the names
                #### end layer freezing
        self.spec_layer = features.STFT(n_fft=1024, freq_bins=None, hop_length=128,
                              window='hann', freq_scale='linear', center=True, pad_mode='reflect',
                           sr=8000, output_format="Magnitude", trainable=True, fmin=300, fmax=3000,)
        self.sizer = VT.Resize((image_size,image_size))
        self.pcen_layer = self.PCENTransform(eps=1e-6, s=0.025, alpha=0.6, delta=0.1, r=0.2, trainable=True)
        #self.augment_layer = augment_audio(trainable = True, sample_rate = config.rate)

    def normalize(self, x):
        size = x.shape
        x_max = x.max(1, keepdim=True)[0] # Finding max values for each frame
        x_min = x.min(1, keepdim=True)[0]
        output = (x-x_min)/(x_max-x_min) # If there is a column with all zero, nan will occur
        output[torch.isnan(output)]=0 # Making nan to 0
        return output

    def forward(self, x):
        # first compute spectrogram
        logging.debug("input shape that goes for augmentation = " + str(x.squeeze().shape))
        #spec = self.augment_layer(x.squeeze())
        logging.debug("Out put of augment and input shape that goes for STFT = " + str(x.shape))
        spec = self.spec_layer(x)  # (B, F, T)
        # normalize
#         spec = spec.transpose(1,2) # (B, T, F)
        logging.debug("Out put of STFT and input shape that goes for PCEN = " + str(spec.shape))
        spec = self.pcen_layer(spec)
        logging.debug("Out put of PCEN and input shape that goes for NORM = " + str(spec.shape))
        spec = self.normalize(spec)

        # then size for CNN model
        # and create a channel
        spec = self.sizer(spec)
        x = spec.unsqueeze(1)
        # then repeat channels
        logging.debug("Final shape that goes to backbone = " + str(x.shape))
        if torch.sum(x) == 0:
            logging.warn("ZERO INPUT in forward")
            x  = x+torch.tensor(1e-6)


        x = self.backbone(x)
        #print("x shape = " + str(x.shape))
        #print("x = " +str(x))
        #pred = nn.Softmax(x)
        pred = x
        #print(np.argmax(pred.detach().cpu().numpy()))
        #print(pred)
        output = {"prediction": pred,
                  "spectrogram": spec}
        #print(output)
        return output
