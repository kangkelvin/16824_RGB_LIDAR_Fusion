import argparse
import os

import torch
import numpy as np
import wandb
from data_loader.data_loader import get_data_loaders
from model.model import RgbLidarFusion
from trainer.trainer import Trainer
from model.loss import YoloLoss
import multiprocessing

SEED = 10
# Set the random seed manually for reproducibility.
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)


def get_args(arg_list=None):
    parser = argparse.ArgumentParser(description='Hell Yeah')
    # setup params
    parser.add_argument('--train_dir', type=str, default="data/dataset")
    parser.add_argument('--val_dir', type=str, default="data/dataset")
    parser.add_argument('--device', default=torch.device("cuda"))
    parser.add_argument('--num_data_loader_workers', type=int, default=multiprocessing.cpu_count())
    # monitor params
    parser.add_argument('--load_checkpoint', type=bool, default=False)
    parser.add_argument('--checkpoint_path', type=str, default="results/checkpoint_epoch6.pth")
    parser.add_argument('--save_best_model', type=bool, default=False)
    parser.add_argument('--save_model_checkpoint', type=bool, default=True)
    parser.add_argument('--save_period', type=int, default=5)  # epoch
    parser.add_argument('--log_period', type=int, default=4)  # iteration
    parser.add_argument('--val_period', type=int, default=1000)  # epoch
    parser.add_argument('--use_wandb', type=bool, default=True)
    # data params
    parser.add_argument('--image_size', type=int, default=448)
    # training params
    parser.add_argument('--batch_size', type=int, default=3)
    parser.add_argument('--num_epochs', type=int, default=60)
    parser.add_argument('--lr', type=float, default=1e-2)
    parser.add_argument('--scheduler_step', type=int, default=10)
    parser.add_argument('--scheduler_gamma', type=float, default=0.1)
    # Pointcloud encoder params
    parser.add_argument('--pc_num_input_features', type=int, default=4)
    parser.add_argument('--pc_use_norm', type=bool, default=True)
    parser.add_argument('--pc_num_filters', type=list[int], default=[64, 128, 128]) # [64, 128, 256]
    parser.add_argument('--pc_with_distance', type=bool, default=False)
    parser.add_argument('--pc_voxel_size', type=list[float], default=[0.32, 0.32, 4])
    parser.add_argument('--pc_range', type=list[float], default=[0, -60, -3, 120, 60, 1])
    parser.add_argument('--pc_max_num_voxels', type=int, default=12000)
    parser.add_argument('--pc_max_num_points_per_voxel', type=int, default=100)
    parser.add_argument('--pc_grid_size', type=list[int])
    # Yolo params
    parser.add_argument('--yolo_anchors', type=list[float], default=[1.56, 1.6, 3.9])  # h, w ,l
    parser.add_argument('--yolo_num_box_per_cell', type=int, default=1)  # use 1 for now to make it easy
    parser.add_argument('--yolo_box_length', type=int, default=9)  # conf, x, y, z, h, w, l, yaw_r, yaw_i
    # Validation params
    parser.add_argument('--visualize_sample', type=bool, default=False)
    parser.add_argument('--ori_img_h', type=int, default=375)
    parser.add_argument('--ori_img_w', type=int, default=1242)
    parser.add_argument('--inference_conf_threshold', type=float, default=0.5)
    parser.add_argument('--NMS_overlap_threshold', type=float, default=0.5)
    parser.add_argument('--MAP_overlap_threshold', type=float, default=0.5)
    args = parser.parse_args() if str is None else parser.parse_args(arg_list)
    return args


def main(args):
    if args.use_wandb:
        wandb.login()
        wandb.init(entity="16824_rgb_lidar_fusion", project="test",
                   config={
                       "lr": args.lr,
                       "batch_size": args.batch_size,
                       "scheduler_step": args.scheduler_step,
                       "scheduler_gamma": args.scheduler_gamma,
                       "num_epochs": args.num_epochs,
                       "notes": "Write your notes about this run here"
                   })

    train_loader, val_loader = get_data_loaders(args)
    model = RgbLidarFusion(args).to(args.device)
    loss_fn = YoloLoss(args, args.pc_range, args.pc_voxel_size, args.yolo_num_box_per_cell, args.yolo_box_length, args.yolo_anchors)
    optimizer = torch.optim.Adam(model.parameters(), args.lr, (0.0, 0.9))
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, args.scheduler_step, args.scheduler_gamma)

    trainer = Trainer(args, model, loss_fn, optimizer, scheduler, train_loader, val_loader)
    if args.visualize_sample:
        trainer.visualize_sample()
    else:
        trainer.train()

    wandb.finish()


if __name__ == '__main__':
    args = get_args()
    main(args)
