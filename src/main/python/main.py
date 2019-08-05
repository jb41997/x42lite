from fbs_runtime.application_context.PySide2 import ApplicationContext
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from requests_futures.sessions import FuturesSession
from waitingspinnerwidget import QtWaitingSpinner
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import sys,os,json,requests,resources,configparser,time,textwrap

if __name__ == '__main__':

	#functions to run in background thread
	class backgroundOps(QObject):

		@Slot()
		def grabWalletName(self):
			wallets=[]
			try:
				responseWalletName=apiSession.get(url=walletURL, timeout=5)
				walletJson=responseWalletName.json()
				walletResponseCode=responseWalletName.status_code
				if walletJson and walletResponseCode==200:
					for wallet in walletJson["walletsFiles"]:
						wallets.append(wallet.split(".")[0])
					grabWalletSig.objSig.emit(wallets)
			except requests.exceptions.RequestException as e:
				displayErrorSig.objSig.emit(["No Wallet Files Found at Host IP: "+swagIP+".  Check IP Setting.",e])
				wallets.append("No Wallets")
				grabWalletSig.objSig.emit(wallets)

		@Slot()
		def buildTransaction(self,txJson):
			try:
				buildTxSession=futuresSession.post(url=buildTxURL, timeout=60, json=txJson, hooks={'response':parseJson})				
				buildTxResult=buildTxSession.result()
				buildTxRespCode=buildTxResult.code
				buildTxJson=buildTxResult.data
				if buildTxJson and buildTxRespCode==200:
					txBuildHex=buildTxJson["hex"]
					submitSendSig.objSig.emit(txBuildHex)
			except requests.exceptions.RequestException as e:
				displayErrorSig.objSig.emit(["Network Error",e])

		@Slot()
		def finalSend(self,data):
			txHex=data
			sendTxParams={"hex":txHex}
			try:
				sendTxSession=futuresSession.post(url=sendTxURL, timeout=60, json=sendTxParams, hooks={'response':parseJson})
				sendTxResult=sendTxSession.result()
				sendTxRespCode=sendTxResult.code
				sendTxJson=sendTxResult.data
				if sendTxJson and sendTxRespCode==200:
					stopSpinSig.workDone.emit()
					displaySuccessSig.workDone.emit()		
			except requests.exceptions.RequestException as e:
				displayErrorSig.objSig.emit(["Network Error",e])
		

		@Slot()
		def constructBalance(self,data):
			balanceJson=data[0]
			balanceRespCode=data[1]
			tempBalanceText=""
			if balanceJson and balanceRespCode==200:
				for balance in balanceJson["balances"]:
					spendableBalance=balance["spendableAmount"]
					unconfirmedBalance=balance["amountUnconfirmed"]
					confirmedBalance=balance["amountConfirmed"]
				tempBalanceText=("<i>Spendable Balance</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<font color='#26bfb5'>"+ str(spendableBalance/100000000) + "</font><font color='#cc147f'><small> x42</small></font><br>"+
				"<i>Confirmed Balance</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<font color='#26bfb5'>"+ str(confirmedBalance/100000000) + "</font><font color='#cc147f'><small> x42</small></font><br>"+
				"<i>Unconfirmed Balance</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<font color='#26bfb5'>"+ str(unconfirmedBalance/100000000) + "</font><font color='#cc147f'><small> x42</small></font>")
			balanceDone.strSig.emit(tempBalanceText)

		@Slot()
		def constructAddress(self,data):
			addressJson=data[0]
			addressRespCode=data[1]
			isUsedAddr=0
			usedAddresses=[]
			tempAddressText=""
			if addressJson and addressRespCode==200:
				for address in addressJson["addresses"]:
					if address["isUsed"]==True:
						usedAddress=address["address"]
						try:
							responseAddrBalance=apiSession.get(url="https://explorer.x42.tech/ext/getbalance/"+usedAddress, timeout=30)
						except requests.exceptions.RequestException as e:
							displayErrorSig.objSig.emit(["Network Error",e])
							return						
						addrBalanceStatus=responseAddrBalance.status_code
						usedAddrBalance=responseAddrBalance.json()
						dType=type(usedAddrBalance).__name__
						if (dType=='float' or dType=='int') and usedAddrBalance>0 and addrBalanceStatus == 200:
							usedAddresses.append([usedAddress,usedAddrBalance])
					elif address["isUsed"]==False and isUsedAddr==0:
						nextUnusedAddr=address["address"]
						isUsedAddr=1
				tempAddressText=("<i>Next Unused Address</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<small>"+nextUnusedAddr+"</small><br>"+
				"<br><i>Used Adresses</i><br>")
				for ad in usedAddresses:
					tempAddressText=(tempAddressText+"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
					tempAddressText=(tempAddressText+"<small>"+ad[0]+" </small><font color='#26bfb5'><small>"+str(ad[1])+"</small></font><font color='#cc147f'><small> x42</small></font><br>")
			addressDone.strSig.emit(tempAddressText)

		@Slot()
		def constructStaking(self,data):
			stakingJson=data[0]
			stakingRespCode=data[1]

			tempStakingText=""
			if stakingJson and stakingRespCode==200:
				if stakingJson["staking"]==True:
					expectedTime=stakingJson["expectedTime"]/3600
					expectHours=int(expectedTime)
					expectMins=(expectedTime*60) % 60
					expectSecs=(expectedTime*3600) % 60
					tempStakingText=("<font color='#979a9a'><small>Estimated stake reward in: %d hours %02d minutes</small></font>" % (expectHours, expectMins))
				else:
					tempStakingText=("<small>Not currently staking</small>")
			stakingDone.strSig.emit(tempStakingText)

		@Slot()
		def constructHistory(self,data):
			walletHistoryJson=data[0]
			historyRespCode=data[1]
			tempHistoryText=""
			recentStakes=0
			preDayStamp=(datetime.now().timestamp()-86400)
			if walletHistoryJson and historyRespCode==200:
				for history in walletHistoryJson["history"]:
					tempHistoryText="<table style='border-collapse:collapse; border-bottom:1px solid white' width='100%' cellspacing='2' cellpadding='2'>"
					for transaction in history["transactionsHistory"]:
						timeInt=int(transaction["timestamp"])
						txType=transaction["type"]
						tempHistoryText=(tempHistoryText+"<tr><td align='center' style='width:30%;'><i>"+txType+"</i></td>")
						tempHistoryText=(tempHistoryText+"<td style='width:30%;'><font color='#26bfb5'>"+"{0:.8f}".format(transaction["amount"]/100000000)+"</font><font color='#cc147f'>  x42 </font></td>")
						tempHistoryText=(tempHistoryText+"<td style='width:39%;'>"+datetime.fromtimestamp(timeInt).strftime('%r on %b %d, %Y')+"</td></tr>")
						if timeInt>preDayStamp and txType=="staked":
							recentStakes+=1
					tempHistoryText=tempHistoryText+"</table>"
			historyDone.strSig.emit(tempHistoryText)
			historyDone.objSig.emit(str(recentStakes))


		@Slot()
		def executeLoad(self):
			global secCounter
			secCounter=0
			try:
				balanceSession=futuresSession.get(url=balanceURL, timeout=30, params=walletParams, hooks={'response':parseJson})
				addressSession=futuresSession.get(url=addressURL, timeout=30, params=walletParams, hooks={'response':parseJson})
				historySession=futuresSession.get(url=walletHistoryURL, timeout=30, params=walletParams, hooks={'response':parseJson})
				stakingSession=futuresSession.get(url=stakingURL, timeout=30, params=walletParams, hooks={'response':parseJson})
				balanceResult=balanceSession.result()
				addressResult=addressSession.result()
				historyResult=historySession.result()
				stakingResult=stakingSession.result()
				#responseCodes=str(balanceResult.code)+" "+str(stakingResult.code)+" "+str(addressResult.code)+" "+str(historyResult.code)
				#print(responseCodes)
				balDocDone.objSig.emit([balanceResult.data,balanceResult.code])
				stakeDocDone.objSig.emit([stakingResult.data,stakingResult.code])
				addrDocDone.objSig.emit([addressResult.data, addressResult.code])
				histDocDone.objSig.emit([historyResult.data,historyResult.code])
			except requests.exceptions.RequestException as e:
				displayErrorSig.objSig.emit(["Network Error",e])

	class QHLine(QFrame):
		def __init__(self, parent=None, color=QColor("black")):
			super(QHLine, self).__init__(parent)
			self.setFrameShape(QFrame.HLine)
			self.setFrameShadow(QFrame.Plain)
			self.setLineWidth(0)
			self.setMidLineWidth(3)
			self.setContentsMargins(0, 0, 0, 0)
			self.setColor(color)

		def setColor(self, color):
			pal = self.palette()
			pal.setColor(QPalette.WindowText, color)
			self.setPalette(pal)


	#Main thread functions
	@Slot()
	def displayError(resp):
		responseCode=resp[0]
		response=resp[1]
		message="There was an error!\n\n{}".format("\n".join(textwrap.wrap(str(responseCode),width=55)))
		msgBox.setText(message)
		#msgBox.setInformativeText("Error: "+str(responseCode))
		msgBox.setDetailedText(str(response))
		msgBox.exec_()
		stopSpin()

	@Slot()
	def displaySuccess():
		sendWalletPassword.clear()
		msgBox.setText("Transaction Sent!")
		msgBox.exec_()

	def parseJson(resp, *args, **kwargs):
		resp.data=resp.json()
		resp.code=resp.status_code

	@Slot()
	def stopSpin():
		waitSpin.stop()

	@Slot()
	def startSpin():
		waitSpin.start()

	#Grab wallet balance
	@Slot()
	def displayBalance(doc):
		balanceArea.setHtml(doc)


	#Grab wallet address info
	@Slot()
	def displayAddressInfo(doc):
		addressArea.setHtml(doc)
		balanceArea.setFixedHeight(balanceArea.document().size().height()+5)
		addressArea.setFixedHeight(balanceArea.document().size().height()+5)
		addressArea.setFixedWidth(addressArea.document().size().width()+20)
		
	#Grab staking info
	@Slot()
	def displayStaking(doc):
		stakingLabel.setText(doc)

	#Grab recent wallet history
	@Slot()
	def displayHistory(doc):
		walletHistoryArea.setHtml(doc)
		walletHistoryArea.verticalScrollBar().setValue(0)
		stopSpin()
		switchToDashboardPage()

	@Slot()
	def updateWalletLabel(stakes):
		historyLabel.setText("<h2><font color='#cc147f'>Wallet History</font><font color='#979a9a'><small> ("+stakes+" rewards in the past 24 hours)</small></font></h2>")

	@Slot()
	def populateWallets(listOfWallets):
		selectWalletName.clear()
		selectWalletName.addItems(listOfWallets)
		stopSpin()

	def initWallets():
		startSpin()
		initiateWalletSig.workDone.emit()

	#copy Address to Clipboard
	def copyAddress(event):
		addrCursor = addressArea.cursorForPosition(event.pos())
		addrCursor.select(QTextCursor.WordUnderCursor)
		copiedAddr=addrCursor.selectedText()
		if len(copiedAddr) == 34:
			addressArea.setTextCursor(addrCursor)
			app.clipboard().setText(copiedAddr)

	def switchToSettingsPage():
		stackedWidget.setCurrentIndex(3)

	def switchToSendPage():
		stackedWidget.setCurrentIndex(2)

	def switchToDashboardPage():
		stackedWidget.setCurrentIndex(1)

	def switchToWalletPage():
		stackedWidget.setCurrentIndex(0)

	def clearForm():
		sendWalletAmount.clear()
		sendWalletPassword.clear()
		sendRecipient.clear()

	def clearDash():
		stakingLabel.clear()
		balanceArea.clear()
		walletHistoryArea.clear()
		addressArea.clear()
		startSpin()
		fireLoad.workDone.emit()

	def closeThread():
		loadThread.exit()

	def closeApp():
		app.quit()

	class workSignal(QObject):
		workDone=Signal()
		strSig=Signal(str)
		objSig=Signal(object)

	#autoRefresh timer
	def updateTimer():
		global secCounter
		global secToRefresh
		if walletName:
			if secCounter < secToRefresh:
				refreshSecond=secToRefresh-secCounter
				mins,secs=divmod(refreshSecond,60)
				autoLabel.clear()
				autoLabel.setText("<font color='#979a9a'><small>(Auto-refresh in: "+"{:02d}:{:02d}".format(mins,secs)+")</small></font>")
				secCounter+=1
			else:
				secCounter=0
				clearDash()

	def chooseWallet():
		global walletName
		global walletParams
		walletName=selectWalletName.currentText()
		walletParams = dict(
				WalletName=walletName,
				AccountName="account 0"
			)
		startSpin()
		fireLoad.workDone.emit()

	def submitSend():
		global walletName
		buildTxParams={
			"password": sendWalletPassword.text(),
		  	"walletName": walletName,
		  	"accountName": "account 0",
		  	"recipients": [
		    	{
		      	"destinationAddress": sendRecipient.text(),
		      	"amount": sendWalletAmount.text()
		    	}
		  	],
		  	"feeType": "low",
		  	"allowUnconfirmed": True,
		  	"shuffleOutputs": True
		  	}
		startSpin()
		transactionSig.objSig.emit(buildTxParams)

	def rebuildURLs(sIP):
		global swagIP
		global swaggerServer
		global walletHistoryURL
		global balanceURL
		global stakingURL
		global addressURL
		global walletURL
		global buildTxURL
		global sendTxURL

		swagIP=sIP
		swaggerServer = "http://"+swagIP
		walletHistoryURL=swaggerServer+historyEndpoint
		balanceURL=swaggerServer+balanceEndpoint
		stakingURL=swaggerServer+stakingEndpoint
		addressURL=swaggerServer+addressEndpoint
		walletURL=swaggerServer+walletEndpoint
		buildTxURL=swaggerServer+buildTxEndpoint
		sendTxURL=swaggerServer+sendTxEndpoint
		switchToWalletPage()
		initWallets()

	def updateSettings():
		xConfig.set('SETTINGS','NODE_HOST',hostSetting.text())
		xConfig.set('SETTINGS','REFRESH_INTERVAL',refreshSetting.text())

		with open(appctxt.get_resource('x42lite.ini'),'w') as configfile:
			xConfig.write(configfile)
		configfile.close()

		secToRefresh=int(xConfig['SETTINGS']['REFRESH_INTERVAL'])
		rebuildURLs(str(xConfig['SETTINGS']['NODE_HOST']))

	def setDefaultSettings():
		hostSetting.setText("127.0.0.1:42220")
		refreshSetting.setText("900")

	#Application Setup
	appctxt=ApplicationContext()
	app =appctxt.app

	# Now use a palette to switch to dark colors:
	palette = QPalette()
	palette.setColor(QPalette.Window, QColor(34, 34, 34))
	palette.setColor(QPalette.WindowText, Qt.white)
	palette.setColor(QPalette.Base, QColor(25, 25, 25))
	palette.setColor(QPalette.AlternateBase, QColor(34, 34, 34))
	palette.setColor(QPalette.ToolTipBase, Qt.white)
	palette.setColor(QPalette.ToolTipText, Qt.white)
	palette.setColor(QPalette.Text, Qt.white)
	palette.setColor(QPalette.Button, QColor(34, 34, 34))
	palette.setColor(QPalette.ButtonText, Qt.white)
	palette.setColor(QPalette.BrightText, Qt.red)
	palette.setColor(QPalette.Link, QColor(42, 130, 218))
	palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
	palette.setColor(QPalette.HighlightedText, Qt.black)
	app.setPalette(palette)

	#Swagger Api settings
	xConfig=configparser.ConfigParser()
	xConfig.read(appctxt.get_resource('x42lite.ini'))
	swagIP=str(xConfig['SETTINGS']['NODE_HOST'])
	swaggerServer = "http://"+swagIP
	historyEndpoint = '/api/Wallet/history'
	balanceEndpoint = '/api/Wallet/balance'
	stakingEndpoint = '/api/Staking/getstakinginfo'
	addressEndpoint = '/api/Wallet/addresses'
	walletEndpoint = '/api/Wallet/files'
	buildTxEndpoint= '/api/Wallet/build-transaction'
	sendTxEndpoint= '/api/Wallet/send-transaction'
	walletHistoryURL=swaggerServer+historyEndpoint
	balanceURL=swaggerServer+balanceEndpoint
	stakingURL=swaggerServer+stakingEndpoint
	addressURL=swaggerServer+addressEndpoint
	walletURL=swaggerServer+walletEndpoint
	buildTxURL=swaggerServer+buildTxEndpoint
	sendTxURL=swaggerServer+sendTxEndpoint

	apiSession = requests.session()
	futuresSession=FuturesSession()

	retryCount=Retry(total=3,backoff_factor=0.1,status_forcelist=(400, 500, 502, 504))
	apiSession.mount('http://', HTTPAdapter(max_retries=retryCount))
	apiSession.mount('https://', HTTPAdapter(max_retries=retryCount))
	futuresSession.mount('http://', HTTPAdapter(max_retries=retryCount))
	futuresSession.mount('https://', HTTPAdapter(max_retries=retryCount))

	#refresh interval
	secToRefresh=int(xConfig['SETTINGS']['REFRESH_INTERVAL'])
	secCounter=0
	
	#GUI	
	QFontDatabase.addApplicationFont(":/base/Roboto-Regular.ttf")
	app.setFont(QFont("Roboto"))
	mainWin=QStackedWidget()
	walletPage=QWidget()
	dashboardPage=QWidget()
	sendPage=QWidget()
	settingsPage=QWidget()
	stackedWidget=QStackedWidget()
	stackedWidget.addWidget(walletPage)
	stackedWidget.addWidget(dashboardPage)
	stackedWidget.addWidget(sendPage)
	stackedWidget.addWidget(settingsPage)
	stackedWidget.setStyleSheet("QStackedWidget {border-image: url(:/base/x42poster_darkened.jpg) 0 0 0 0 stretch stretch;} QMessageBox,QComboBox {background-color: rgba(34, 34, 34, 1.0);} QLineEdit {background-color: rgba(34, 34, 34, 0.8); border:1px solid #000000;} QPushButton {background-color: #4717F6; background-image: none;} QPushButton::Hover {background-color: #4114e5;} QTextEdit {background-color: rgba(34, 34, 34, 0.7); border:1px solid #000000;} QScrollBar,QScrollBar::handle {background:rgba(34, 34, 34, 0.7); border:1px solid #000000;} QScrollBar::add-page,QScrollBar::sub-page,QScrollBar::add-line,QScrollBar::sub-line{background: none; border: none;}" )
	mainWin.addWidget(stackedWidget)
	
	#Dashboard Page
	geom = app.desktop().availableGeometry()
	walletHistoryArea=QTextEdit()
	walletHistoryArea.setReadOnly(1)
	walletHistoryArea.setLineWrapMode(QTextEdit.NoWrap)
	walletHistoryArea.setAcceptRichText(1)
	balanceArea=QTextEdit()
	balanceArea.setReadOnly(1)
	balanceArea.setLineWrapMode(QTextEdit.NoWrap)
	balanceArea.setAcceptRichText(1)
	addressArea=QTextEdit()
	addressArea.setReadOnly(1)
	addressArea.setLineWrapMode(QTextEdit.NoWrap)
	addressArea.setAcceptRichText(1)
	historyLabel=QLabel()
	balanceLabel=QLabel()
	addressLabel=QLabel()
	stakingLabel=QLabel()
	logoLabel=QLabel()
	sendLogoLabel=QLabel()
	settingsLogoLabel=QLabel()
	walletLogoLabel=QLabel()
	autoLabel=QLabel()
	autoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	xImage=QPixmap(":/base/x42logo.png")
	xSendIcon=QIcon(":/base/x42logo_send.png")
	xDashboardIcon=QIcon(":/base/x42logo_dashboard.png")
	xSettingsIcon=QIcon(":/base/cog.png")
	logoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
	logoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	sendLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
	sendLogoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	settingsLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
	settingsLogoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	walletLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
	walletLogoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	refreshButton=QPushButton("Refresh")
	refreshButton.setStyleSheet("max-width: 60px; max-height: 30px;")
	sendButton=QPushButton()
	sendButton.setStyleSheet("min-width: 80px; max-height: 30px;")
	sendButton.setIcon(xSendIcon)
	sendButton.setIconSize(QSize(80,21))
	homeButton=QPushButton("Home")
	homeButton.setStyleSheet("max-width: 60px; max-height: 30px;")
	hLine=QHLine()
	hLine.setColor(QColor(71,23,246))
	vDashboardLayout = QVBoxLayout()
	hFooterLayout=QHBoxLayout()
	hFooterLayout.addWidget(stakingLabel)
	hFooterLayout.addStretch(1)
	hFooterLayout.addWidget(autoLabel)
	hFooterLayout.addWidget(refreshButton)
	hFooterLayout.addWidget(homeButton)
	hBalanceLayout=QHBoxLayout()
	hBalanceLayout.addWidget(balanceLabel)
	hBalanceLayout.addStretch(1)
	vBalanceLayout=QVBoxLayout()
	vBalanceLayout.addStretch(1)
	vBalanceLayout.addLayout(hBalanceLayout)
	vBalanceLayout.addWidget(balanceArea)
	vBalanceLayout.addStretch(1)
	vAddressLayout=QVBoxLayout()
	vAddressLayout.addStretch(1)
	vAddressLayout.addWidget(addressLabel)
	vAddressLayout.addWidget(addressArea)
	vAddressLayout.addStretch(1)
	hMidLayout=QHBoxLayout()
	hMidLayout.addLayout(vBalanceLayout)
	hMidLayout.addLayout(vAddressLayout)
	hHeaderLayout=QHBoxLayout()
	hHeaderLayout.addWidget(sendButton)
	hHeaderLayout.addWidget(logoLabel)
	vDashboardLayout.addLayout(hHeaderLayout)
	vDashboardLayout.addLayout(hMidLayout)
	vDashboardLayout.addWidget(hLine)
	vDashboardLayout.addWidget(historyLabel)
	vDashboardLayout.addWidget(walletHistoryArea)
	vDashboardLayout.addLayout(hFooterLayout)
	balanceLabel.setText("<h2><font color='#cc147f'>Balances</font></h2>")
	addressLabel.setText("<h2><font color='#cc147f'>Addresses</font><font color='#979a9a'><small> (click address to copy)</small></font></h2>")
	historyLabel.setText("<h2><font color='#cc147f'>Wallet History</font></h2>")
	dashboardPage.setLayout(vDashboardLayout)

	#wallet select page
	submitWalletButton=QPushButton("GO!")
	submitWalletButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	refreshWalletButton=QPushButton("Refresh")
	refreshWalletButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	clearWalletButton=QPushButton("Close")
	clearWalletButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	settingsButton=QPushButton()
	#settingsButton.setFlat(1)
	settingsButton.setIcon(xSettingsIcon)
	settingsButton.setIconSize(QSize(15,15))
	settingsButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	hWalletFormLayout=QHBoxLayout()
	walletFormLayout=QFormLayout()
	walletFormLayout.setLabelAlignment(Qt.AlignRight)
	vWalletLayout=QVBoxLayout()
	vWalletFormButtonsLayout=QHBoxLayout()
	vWalletFormButtonsLayout.addStretch(1)
	vWalletFormButtonsLayout.addWidget(settingsButton)
	vWalletFormButtonsLayout.addWidget(refreshWalletButton)
	vWalletFormButtonsLayout.addWidget(clearWalletButton)
	vWalletFormButtonsLayout.addWidget(submitWalletButton)
	vWalletFormButtonsLayout.addStretch(1)
	vWalletFormButtonsLayout.setAlignment(Qt.AlignTop)
	selectWalletName=QComboBox()
	selectWalletName.setFixedWidth(200)
	selectWalletName.setEditable(True)
	selectWalletName.lineEdit().setReadOnly(True)
	selectWalletName.lineEdit().setAlignment(Qt.AlignCenter)
	hWalletHeaderLayout=QHBoxLayout()
	hWalletHeaderLayout.addWidget(walletLogoLabel)
	walletFormLayout.addRow(walletFormLayout.tr("&Choose Wallet:"),selectWalletName)
	hWalletFormLayout.addStretch(1)
	hWalletFormLayout.addLayout(walletFormLayout)
	hWalletFormLayout.addStretch(1)
	hWalletFormLayout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
	hWalletHeaderLayout.setAlignment(Qt.AlignTop)
	vWalletLayout.addLayout(hWalletHeaderLayout)
	vWalletLayout.addLayout(hWalletFormLayout)
	vWalletLayout.addLayout(vWalletFormButtonsLayout)
	walletPage.setLayout(vWalletLayout)

	#Settings Page
	saveSettingsButton=QPushButton("Save")
	saveSettingsButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	cancelSettingsButton=QPushButton("Cancel")
	cancelSettingsButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	defaultSettingsButton=QPushButton("Defaults")
	defaultSettingsButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	hSettingsFormLayout=QHBoxLayout()
	vSettingsLayout=QVBoxLayout()
	settingsFormLayout=QFormLayout()
	settingsFormLayout.setLabelAlignment(Qt.AlignRight)
	hSettingsHeaderLayout=QHBoxLayout()
	hSettingsButtonsLayout=QHBoxLayout()
	hSettingsButtonsLayout.addStretch(1)
	hSettingsButtonsLayout.addWidget(cancelSettingsButton)
	hSettingsButtonsLayout.addWidget(defaultSettingsButton)
	hSettingsButtonsLayout.addWidget(saveSettingsButton)
	hSettingsButtonsLayout.addStretch(1)
	hSettingsButtonsLayout.setAlignment(Qt.AlignTop)
	hSettingsHeaderLayout.addStretch(1)
	hSettingsHeaderLayout.addWidget(settingsLogoLabel)
	hSettingsHeaderLayout.setAlignment(Qt.AlignTop)
	hostSetting=QLineEdit()
	hostSetting.setFixedWidth(200)
	hostSetting.setText(swagIP)
	refreshSetting=QLineEdit()
	refreshSetting.setFixedWidth(200)
	refreshSetting.setText(str(secToRefresh))
	settingsFormLayout.addRow(settingsFormLayout.tr("&Node Address <font color='#979a9a'><small>(IP and Port)</small></font>: "),hostSetting)
	settingsFormLayout.addRow(settingsFormLayout.tr("&Auto Refresh Timer <font color='#979a9a'><small>(In Seconds)</small></font>: "),refreshSetting)
	hSettingsFormLayout.addStretch(1)
	hSettingsFormLayout.addLayout(settingsFormLayout)
	hSettingsFormLayout.addStretch(1)
	hSettingsFormLayout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
	vSettingsLayout.addLayout(hSettingsHeaderLayout)
	vSettingsLayout.addLayout(hSettingsFormLayout)
	vSettingsLayout.addLayout(hSettingsButtonsLayout)
	settingsPage.setLayout(vSettingsLayout)

	#Send page 
	dashboardButton=QPushButton()
	dashboardButton.setStyleSheet("min-width: 80px; max-height: 30px;")
	dashboardButton.setIcon(xDashboardIcon)
	dashboardButton.setIconSize(QSize(155,26))
	submitButton=QPushButton("Submit")
	submitButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	clearButton=QPushButton("Clear")
	clearButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	hSendFormLayout=QHBoxLayout()
	sendFormLayout=QFormLayout()
	sendFormLayout.setLabelAlignment(Qt.AlignRight)
	vSendLayout=QVBoxLayout()
	hFormButtonsLayout=QHBoxLayout()
	hFormButtonsLayout.addStretch(1)
	hFormButtonsLayout.addWidget(clearButton)
	hFormButtonsLayout.addWidget(submitButton)
	hFormButtonsLayout.addStretch(1)
	hFormButtonsLayout.setAlignment(Qt.AlignTop)
	sendWalletAmount=QLineEdit()
	sendWalletAmount.setFixedWidth(350)
	sendAmountValidator=QDoubleValidator()
	sendAmountValidator.setDecimals(8)
	sendWalletAmount.setValidator(sendAmountValidator)
	sendWalletPassword=QLineEdit()
	sendWalletPassword.setEchoMode(QLineEdit.Password)
	sendWalletPassword.setFixedWidth(350)
	sendRecipient=QLineEdit()
	sendRecipient.setFixedWidth(350)
	regExp = QRegExp("^[a-zA-Z0-9]{0,34}$")
	regExpValidator=QRegExpValidator(regExp)
	sendRecipient.setValidator(regExpValidator)
	hSendHeaderLayout=QHBoxLayout()
	hSendHeaderLayout.addWidget(dashboardButton)
	hSendHeaderLayout.addWidget(sendLogoLabel)
	hSendHeaderLayout.setAlignment(Qt.AlignTop)
	sendFormLayout.addRow(sendFormLayout.tr("&Amount to send:"),sendWalletAmount)
	sendFormLayout.addRow(sendFormLayout.tr("&Recipient Address:"),sendRecipient)
	sendFormLayout.addRow(sendFormLayout.tr("&Wallet Password:"),sendWalletPassword)
	hSendFormLayout.addStretch(1)
	hSendFormLayout.addLayout(sendFormLayout)
	hSendFormLayout.addStretch(1)
	hSendFormLayout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
	vSendLayout.addLayout(hSendHeaderLayout)
	vSendLayout.addLayout(hSendFormLayout)
	vSendLayout.addLayout(hFormButtonsLayout)
	sendPage.setLayout(vSendLayout)

	msgBox=QMessageBox(parent=stackedWidget)
	mainWin.setFixedSize(geom.width()*.5, geom.height() *.6)
	mainWin.show()

	#waiting spinner
	waitSpin=QtWaitingSpinner(mainWin,True,True,Qt.ApplicationModal)
	waitSpin.setColor(QColor(255,255,255))

	#Signals
	startSpinSig=workSignal()
	stopSpinSig=workSignal()
	grabWalletSig=workSignal()
	initiateWalletSig=workSignal()
	submitSendSig=workSignal()
	transactionSig=workSignal()
	balDocDone=workSignal()
	addrDocDone=workSignal()
	histDocDone=workSignal()
	stakeDocDone=workSignal()
	balanceDone=workSignal()
	addressDone=workSignal()
	stakingDone=workSignal()
	historyDone=workSignal()
	displaySuccessSig=workSignal()
	displayErrorSig=workSignal()
	fireLoad=workSignal()

	loadThread=QThread()
	loadThread.start()
	loadDashboard=backgroundOps()
	loadDashboard.moveToThread(loadThread)
	grabWalletSig.objSig.connect(populateWallets)
	initiateWalletSig.workDone.connect(loadDashboard.grabWalletName)
	transactionSig.objSig.connect(loadDashboard.buildTransaction)
	submitSendSig.objSig.connect(loadDashboard.finalSend)
	fireLoad.workDone.connect(loadDashboard.executeLoad)
	balDocDone.objSig.connect(loadDashboard.constructBalance)
	histDocDone.objSig.connect(loadDashboard.constructHistory)
	addrDocDone.objSig.connect(loadDashboard.constructAddress)
	stakeDocDone.objSig.connect(loadDashboard.constructStaking)
	balanceDone.strSig.connect(displayBalance)
	addressDone.strSig.connect(displayAddressInfo)
	stakingDone.strSig.connect(displayStaking)
	historyDone.strSig.connect(displayHistory)
	historyDone.objSig.connect(updateWalletLabel)
	startSpinSig.workDone.connect(startSpin)
	stopSpinSig.workDone.connect(stopSpin)
	displaySuccessSig.workDone.connect(displaySuccess)
	displayErrorSig.objSig.connect(displayError)

	refreshTimer=QTimer()
	refreshTimer.timeout.connect(updateTimer)
	refreshTimer.start(1000)

	settingsButton.clicked.connect(switchToSettingsPage)
	defaultSettingsButton.clicked.connect(setDefaultSettings)
	cancelSettingsButton.clicked.connect(switchToWalletPage)
	saveSettingsButton.clicked.connect(updateSettings)
	refreshButton.clicked.connect(clearDash)
	sendButton.clicked.connect(switchToSendPage)
	clearButton.clicked.connect(clearForm)
	submitButton.clicked.connect(submitSend)
	dashboardButton.clicked.connect(switchToDashboardPage)
	submitWalletButton.clicked.connect(chooseWallet)
	refreshWalletButton.clicked.connect(initWallets)
	homeButton.clicked.connect(switchToWalletPage)
	clearWalletButton.clicked.connect(closeApp)
	addressArea.mouseReleaseEvent=copyAddress

	walletName=""
	walletParams={}
	initWallets()

	app.aboutToQuit.connect(closeThread)
	app.exec_()


