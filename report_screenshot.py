from PyQt5 import QtWidgets
import sys
from ui_to_pic_ import Ui_MainWindow


def make_pic_from_instrument(line1: tuple, asset_name: str, quantity: str, current_price: str, average_price: str,
                             current_sum: str, share: str, total_change: str, total_change_per: str,
                             previous_change: str, previous_change_per: str) -> None:

    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_MainWindow()
    ui.setupUi(Form)

    # first row of picture
    # total sum
    ui.Col5_label.setText(f'{line1[0]}')
    # total change
    ui.Col7_label.setText(f'{line1[1]}')
    # total change per
    ui.Col8_label.setText(f'{line1[2]}')
    # prev change
    ui.Col91_label.setText(f'{line1[3]}')
    # prev change per
    ui.Col92_label.setText(f'{line1[4]}')

    # assets names
    ui.Col1_Row2_label.setText(asset_name)
    # quantity
    ui.Col2_Row2_label.setText(quantity)
    # current price
    ui.Col3_Row2_label.setText(current_price)
    # avg price
    ui.Col4_Row2_label.setText(average_price)
    # sum
    ui.Col5_Row2_label.setText(current_sum)
    # share
    ui.Col6_Row2_label.setText(share)
    # total change
    ui.Col7_Row2_label.setText(total_change)
    # total change per
    ui.Col8_Row2_label.setText(total_change_per)
    # prev change
    ui.Col91_Row2_label.setText(previous_change)
    #
    ui.Col92_Row2_label.setText(previous_change_per)

    Form.grab().save('save.jpg', 'jpg', quality=85)
    app.quit()
