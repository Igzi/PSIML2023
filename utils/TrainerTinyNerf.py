import time
from datetime import datetime
import torch
import numpy as np
from utils.Trainer import Trainer
from utils.Camera import Camera
import matplotlib.pyplot as plt

class TrainerTinyNerf(Trainer):
    def __init__(self, model, device, images, cameras, renderer, config):
        super().__init__(model, device, images, cameras, renderer, config)
    
    def train(self, test_img, test_pose, focal):
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        
        self.model.to(self.device)

        optimizer = torch.optim.Adam(self.model.parameters(),lr=self.lr)
        criterion = torch.nn.MSELoss()

        test_camera = Camera(test_img.shape[1], test_img.shape[2], test_pose[0], focal)
        psnr_list = []
        start = time.time()
        for i in range(self.max_epochs):
            optimizer.zero_grad()

            rnd_img = np.random.randint(0, self.images.shape[0])
            img = self.images[rnd_img]
            
            ray_origins, ray_dirs = self.cameras[rnd_img].getRays()
            
            points, dists = self.renderer.getSparsePoints(ray_origins, ray_dirs)
            
            rgb = self.renderer.getPixelValues(self.model, points, dists)
            loss = criterion(rgb, img.reshape((-1,3)).to(rgb.device))
            
            loss.backward()
            optimizer.step()

            if i % self.checkpoint_step == 0 and i > 0:
                now = datetime.now()
                dt_string = now.strftime("%d%m%Y%H%M%S")
                torch.save({
                    'epoch': i,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'train_loss_history': psnr_list,
                    }, self.checkpoint_path + f"{dt_string}.pt")

            if i % self.stats_step == 0:
                print(f'Epoch: {i}, Loss: {loss.item()}, Secs per iter: {(time.time()-start)/self.stats_step}')
                start = time.time()
                
                test_o, test_d = test_camera.getRays()
                test_o = test_o.to(rgb.device)
                test_d= test_d.to(rgb.device)
                
                test_points, test_dists = self.renderer.getSparsePoints(test_o, test_d)
                with torch.no_grad():
                    test_rgb = self.renderer.getPixelValues(self.model, test_points, test_dists)
                    test_loss = criterion(test_rgb, test_img.reshape((-1,3)).to(test_rgb.device))
                    test_psnr = -10*torch.log10(test_loss)
                    psnr_list.append(test_psnr.item())
                
                print(f'Test PSNR: {test_psnr.item()}')
                print(test_rgb.shape)
                plt.subplot(2,2,3)
                plt.imshow(test_rgb.cpu().reshape((100,100,3)).numpy())
                plt.subplot(2,2,4)
                plt.imshow(test_img[0])
                plt.subplot(2,1,1)
                plt.plot(psnr_list)
                plt.show()
