if [ -z "$1" ]
then
	echo "Must specify Jackfish root directory."
	exit 1
fi

JACKFISH_DIR=$1

pyuic5 -o $JACKFISH_DIR/jackfish/gui/main_gui.py $JACKFISH_DIR/jackfish/gui/main_gui.ui
pyuic5 -o $JACKFISH_DIR/jackfish/gui/review_gui.py $JACKFISH_DIR/jackfish/gui/review_gui.ui
pyuic5 -o $JACKFISH_DIR/jackfish/gui/cam_gui.py $JACKFISH_DIR/jackfish/gui/cam_gui.ui
pyuic5 -o $JACKFISH_DIR/jackfish/gui/daq_gui.py $JACKFISH_DIR/jackfish/gui/daq_gui.ui
