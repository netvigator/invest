#!/usr/bin/env bash
cd ~/Devel/invest
source ~/.virtualenvs/invest/bin/activate
python -c "from collect import updateAssetsFileMaybe, updateFlowsFileMaybe; updateAssetsFileMaybe(); updateFlowsFileMaybe()"
