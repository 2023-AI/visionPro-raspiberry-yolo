yolo识别.zip是作用于识别番茄用途，是调节AI的自信度来达到最好的识别效果

Dofbot4.zip是作Apple VisionPro连接树莓派机械臂用途，并且能提供虚拟操作面板，控制VisionPro的代碼路徑在 Dofbot 4.zip\Dofbot\Dofbot，裏面的全部swift文件全部都要運行才能成功連接並控制樹莓派

control.py是操控树莓派运动的代码，并且能接收VisionPro的指令

如果想看Demo，請先看清楚"解壓縮教程.txt"文件

最最重要步驟：1.先運行yolo的代碼 2.運行全部swift文件，直至VisionPro彈出"連接樹莓派"的界面 3.在樹莓派中的Jupyterlab(password:yahboom)中運行control.py 4.回到VisionPro，按"連接"按鈕即可連上并可操控樹莓派機械臂運動
