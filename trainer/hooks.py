"""Implementation of several hooks that used in a Trainer class."""
from operator import itemgetter

import torch

from tqdm import tqdm

from .utils import AverageMeter


def train_hook_default(
    model,
    loader,
    loss_fn,
    optimizer,
    device,
    data_getter=itemgetter("image"),
    target_getter=itemgetter("mask"),
    iterator_type=tqdm,
    prefix="",
    stage_progress=False
):
    """ Default train loop function.

    Arguments:
        model (nn.Module): torch model which will be train.
        loader (torch.utils.DataLoader): dataset loader.
        loss_fn (callable): loss function.
        optimizer (torch.optim.Optimizer): Optimizer.
        device (str): Specifies device at which samples will be uploaded.
        data_getter (Callable): function object to extract input data from the sample prepared by dataloader.
        target_getter (Callable): function object to extract target data from the sample prepared by dataloader.
        iterator_type (iterator): type of the iterator.
        prefix (string): prefix which will be add to the description string.
        stage_progress (bool): if True then progress bar will be show.

    Returns:
        Dictionary of output metrics with keys:
            loss: average loss.
    """
    model = model.train()
    iterator = iterator_type(loader, disable=not stage_progress, dynamic_ncols=True)
    loss_avg = AverageMeter()
    for i, sample in enumerate(iterator):
        optimizer.zero_grad()
        inputs = data_getter(sample).to(device)
        targets = target_getter(sample).to(device)
        predicts = model(inputs)
        loss = loss_fn(predicts, targets)
        loss.backward()
        optimizer.step()
        loss_avg.update(loss.item())
        status = "{0}[Train] Loss: {2:.3f} LR:  {4:.5f}".format(
            prefix, i, loss_avg.avg, loss_avg.val, optimizer.param_groups[0]["lr"]
        )
        iterator.set_description(status)
    return {"loss": loss_avg.avg}

def test_hook_default(
    model,
    loader,
    loss_fn,
    metric_fn,
    device,
    data_getter=itemgetter("image"),
    target_getter=itemgetter("mask"),
    iterator_type=tqdm,
    prefix="",
    stage_progress=False,
    get_key_metric=itemgetter("accuracy")
):
    """ Default test loop function.

    Arguments:
        model (nn.Module): torch model which will be train.
        loader (torch.utils.DataLoader): dataset loader.
        loss_fn (callable): loss function.
        metric_fn (callable): evaluation metric function.
        device (str): Specifies device at which samples will be uploaded.
        data_getter (Callable): function object to extract input data from the sample prepared by dataloader.
        target_getter (Callable): function object to extract target data from the sample prepared by dataloader.
        iterator_type (iterator): type of the iterator.
        prefix (string): prefix which will be add to the description string.
        stage_progress (bool): if True then progress bar will be show.

    Returns:
        Dictionary of output metrics with keys:
            metric: output metric.
            loss: average loss.
    """
    model = model.eval()
    iterator = iterator_type(loader, disable=not stage_progress, dynamic_ncols=True)
    loss_avg = AverageMeter()
    metric_fn.reset()
    for i, sample in enumerate(iterator):
        inputs = data_getter(sample).to(device)
        targets = target_getter(sample).to(device)
        with torch.no_grad():
            predict = model(inputs)
            loss = loss_fn(predict, targets)
        loss_avg.update(loss.item())
        predict = predict.softmax(dim=1).detach()
        metric_fn.update_value(predict, targets)
        status = "{0}[Test ] Loss: {2:.3f}".format(prefix, i, loss_avg.avg)
        if get_key_metric is not None:
            status = status + " Acc: {0:.3f}".format(get_key_metric(metric_fn.get_metric_value()))
        iterator.set_description(status)
    output = {"metric": metric_fn.get_metric_value(), "loss": loss_avg.avg}
    return output


def end_epoch_hook_classification(iterator, epoch, output_train, output_test):
    """ Default end_epoch_hook for classification tasks.
    Arguments:
        iterator (iter): iterator.
        epoch (int): number of epoch to store.
        output_train (dict): description of the train stage.
        output_test (dict): description of the test stage.
        trainer (Trainer): trainer object.
    """
    if hasattr(iterator, "set_description"):
        iterator.set_description(
            "test_top1: {1:.3f} train_loss: {2:.3f} test_loss: {3:.3f} ".format(
                epoch, output_test["metric"]["top1"], output_train["loss"], output_test["loss"]
            )
        )
