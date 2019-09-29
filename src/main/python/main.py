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

import sys,os,platform,shutil,json,requests,resources,configparser,time,textwrap

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
					if walletJson["walletsFiles"]:
						for wallet in walletJson["walletsFiles"]:
							wallets.append(wallet.split(".")[0])
					else:
						wallets.append("No Wallets")
					grabWalletSig.objSig.emit(wallets)
			except requests.exceptions.RequestException as e:
				displayErrorSig.objSig.emit(["No Wallet Files Found at Host IP: "+swagIP+".  Check IP Setting.",e])
				wallets.append("No Wallets")
				grabWalletSig.objSig.emit(wallets)

		@Slot()
		def crWalletWorker(self,params):
			which=params[0]
			name=params[1]
			passW=params[2]
			passP=params[3]
			mnem=params[4]
			if which==1:
				try:
					mnemSession=futuresSession.get(url=mnemonicURL, timeout=30, hooks={'response':parseJson})
					mnemResult=mnemSession.result()
					mnemRespCode=mnemResult.code
					mnemRespData=mnemResult.data
					if mnemRespData and mnemRespCode==200:
						createReqJson={"mnemonic": mnemRespData, "password": passW, "passphrase": passP, "name": name}
						createWallSession=futuresSession.post(url=createWalletURL, timeout=30, json=createReqJson, hooks={'response':parseJson})	
						createWallResult=createWallSession.result()
						createWallCode=createWallResult.code
						createWallData=createWallResult.data
						if createWallData and createWallCode==200:
							dispCreateSuccessSig.strSig.emit(createWallData)
				except requests.exceptions.RequestException as e:
					displayErrorSig.objSig.emit(["Network Error",e])
			elif which==2:
				try:
					restoreReqJson={"mnemonic": mnem, "password": passW, "passphrase": passP, "name": name}
					restoreWallSession=futuresSession.post(url=restoreWalletURL, timeout=30, json=restoreReqJson, hooks={'response':parseJson})
					restoreWallResult=restoreWallSession.result()
					restoreWallCode=restoreWallResult.code
					if restoreWallCode==200:
						dispCreateSuccessSig.workDone.emit()
				except requests.exceptions.RequestException as e:
					displayErrorSig.objSig.emit(["Network Error",e])

		@Slot()
		def getNodeStatus(self):
			try:
				statusSession=futuresSession.get(url=nodeStatusURL, timeout=5)
				statusResult=statusSession.result()
				statusResponseCode=statusResult.status_code
				statusJson=statusResult.text
				if statusJson and statusResponseCode==200:
					nodeStatusSig.objSig.emit(statusJson)
			except requests.exceptions.RequestException as e:
				displayErrorSig.objSig.emit(["Node Not Running on "+swagIP,e])

		@Slot()
		def buildTransaction(self,txJson):
			try:
				buildTxSession=futuresSession.post(url=buildTxURL, timeout=30, json=txJson, hooks={'response':parseJson})				
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
				sendTxSession=futuresSession.post(url=sendTxURL, timeout=30, json=sendTxParams, hooks={'response':parseJson})
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
				tempBalanceText=(cssStyle+"<i>Spendable Balance</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<font class='amount-text'><b>"+ str(spendableBalance/100000000) + "</b></font><font class='x-text'><small> x42</small></font><br>"+
				"<i>Confirmed Balance</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<font class='amount-text'><b>"+ str(confirmedBalance/100000000) + "</b></font><font class='x-text'><small> x42</small></font><br>"+
				"<i>Unconfirmed Balance</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<font class='amount-text'><b>"+ str(unconfirmedBalance/100000000) + "</b></font><font class='x-text'><small> x42</small></font>")
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
				tempAddressText=(cssStyle+"<i>Next Unused Address</i><br>"+
				"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"+
				"<small>"+nextUnusedAddr+"</small><br>"+
				"<br><i>Used Adresses</i><br>")
				for ad in usedAddresses:
					tempAddressText=(tempAddressText+"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;")
					tempAddressText=(tempAddressText+"<small>"+ad[0]+" </small><font class='amount-text'><small><b>"+str(ad[1])+"</b></small></font><font class='x-text'><small> x42</small></font><br>")
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
					tempHistoryText=cssStyle+"<table style='border-collapse:collapse; border-bottom:1px solid white' width='100%' cellspacing='2' cellpadding='2'>"
					for transaction in history["transactionsHistory"]:
						timeInt=int(transaction["timestamp"])
						txType=transaction["type"]
						tempHistoryText=(tempHistoryText+"<tr><td align='center' style='width:30%;'><i>"+txType+"</i></td>")
						tempHistoryText=(tempHistoryText+'<td style="width:30%;"><font class="amount-text"><b>'+"{0:.8f}".format(transaction["amount"]/100000000)+'</b></font><font class="x-text">  x42 </font></td>')
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
		msgBox.setDetailedText(str(response))
		stopSpin()
		msgBox.exec_()

	@Slot()
	def displayRestore():
		stopSpin()
		clearCRForm()
		switchToWalletPage()
		initWallets()
		message="Success! Wallet Recovered!"
		msgBox.setText(message)
		msgBox.exec_()

	@Slot()
	def displayCreate(mnemFinal):
		stopSpin()
		clearCRForm()
		switchToWalletPage()
		initWallets()
		recWordsEnum=""
		for i,item in enumerate(mnemFinal.split(" "),1):
			recWordsEnum=recWordsEnum+str(i)+".&nbsp;"+item+"&nbsp;&nbsp;&nbsp;&nbsp;"
			if i % 4 ==0:
				recWordsEnum=recWordsEnum+"<br>"
		message="Success! Wallet Created!<br><br><font color='#B33A3A'>IMPORTANT!</font>{}".format("".join(textwrap.wrap(" Secure the following words along with your password and passphrase.  They are required for wallet recovery.<br><br>"+recWordsEnum,width=55,drop_whitespace=False)))
		msgBox.setText(message)
		msgBox.exec_()

	@Slot()
	def displaySuccess():
		sendWalletPassword.clear()
		msgBox.setText("Transaction Sent!")
		msgBox.exec_()

	def parseJson(resp, *args, **kwargs):
		resp.code=resp.status_code
		try:
			resp.data=resp.json()
		except:
			resp.data={"message": "No Json Data"}
		

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
		historyLabel.setText("<h2>Wallet History<font color='#979a9a'><small> ("+stakes+" rewards in the past 24 hours)</small></font></h2>")

	@Slot()
	def populateWallets(listOfWallets):
		selectWalletName.clear()
		selectWalletName.addItems(listOfWallets)
		stopSpin()

	@Slot()
	def buildStatusArea(statusText):
		statusArea.clear()
		statusArea.setText(statusText)
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


	def switchToStatusPage():
		statusArea.clear()
		nodeStatusSig.workDone.emit()
		stackedWidget.setCurrentIndex(5)
		startSpin()

	def switchToCreateRestorePage():
		clearCRForm()
		stackedWidget.setCurrentIndex(4)

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

	def createRestoreDecision():
		whichCR=selectCR.currentIndex()
		passW=crWalletPassword.text()
		passP=crWalletPassphrase.text()
		passWcheck=crWalletPasswordCheck.text()
		passPcheck=crWalletPassphraseCheck.text()
		wName=crWalletName.text()
		mnem=crMnemonic.text()

		crParams=[whichCR,wName,passW,passP,mnem]
		if whichCR==1:
			if "" not in (passW,passP,passWcheck,passPcheck,wName):
				if passW==passWcheck and passP==passPcheck:
					startSpin()
					whichCRSig.objSig.emit(crParams)
				else:
					displayError(["Password or Passphrase Doesn't Match",""])
			else:
				displayError(["Make Sure All Fields Are Populated",""])
		elif whichCR==2:
			if "" not in (passW,passP,wName,mnem):
				startSpin()
				whichCRSig.objSig.emit(crParams)
			else:
				displayError(["Make Sure All Fields Are Populated",""])

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
		global mnemonicURL
		global createWalletURL
		global restoreWalletURL
		global nodeStatusURL

		swagIP=sIP
		swaggerServer = "http://"+swagIP
		walletHistoryURL=swaggerServer+historyEndpoint
		balanceURL=swaggerServer+balanceEndpoint
		stakingURL=swaggerServer+stakingEndpoint
		addressURL=swaggerServer+addressEndpoint
		walletURL=swaggerServer+walletEndpoint
		buildTxURL=swaggerServer+buildTxEndpoint
		sendTxURL=swaggerServer+sendTxEndpoint
		mnemonicURL=swaggerServer+mnemonicEndpoint
		createWalletURL=swaggerServer+createWalletEndpoint
		restoreWalletURL=swaggerServer+restoreWalletEndpoint
		nodeStatusURL=swaggerServer+nodeStatusEndpoint
		switchToWalletPage()
		initWallets()

	def updateSettings():
		xConfig.set('SETTINGS','NODE_HOST',hostSetting.text())
		xConfig.set('SETTINGS','REFRESH_INTERVAL',refreshSetting.text())
		xConfig.set('SETTINGS','THEME',str(selectStyleName.currentIndex()))

		with open(configPath,'w') as configfile:
			xConfig.write(configfile)
		configfile.close()

		secToRefresh=int(xConfig['SETTINGS']['REFRESH_INTERVAL'])
		rebuildURLs(str(xConfig['SETTINGS']['NODE_HOST']))

	def setDefaultSettings():
		hostSetting.setText("127.0.0.1:42220")
		refreshSetting.setText("900")
		selectStyleName.setCurrentIndex(0)

	def changeStyle(style):
		global cssStyle
		#Dark
		if style==0:
			cssStyle="<style>.amount-text {color: #26bfb5;} .x-text {color: #cc147f;} .hyper-text{color:rgba(204,20,127,.8)}</style>"
			stackedWidget.setStyleSheet("QStackedWidget {border-image: url(:/base/x42poster_darkened.jpg) 0 0 0 0 stretch stretch; color: #FFFFFF;} QLabel{color: #FFFFFF;} QLabel#heading {color: #cc147f;} QMessageBox,QComboBox,QAbstractItemView {background-color: rgba(34, 34, 34, 1.0); color: #FFFFFF;} QLineEdit {background-color: rgba(34, 34, 34, 0.8); color: #FFFFFF; border:1px solid #000000;} QPushButton {background-color: #4717F6; background-image: none; color: #FFFFFF;} QPushButton::Hover {background-color: #4114e5;} QTextEdit {background-color: rgba(34, 34, 34, 0.7); color: #FFFFFF; border:1px solid #000000;} QScrollBar,QScrollBar::handle {background:rgba(34, 34, 34, 0.7); border:1px solid #000000;} QScrollBar::add-page,QScrollBar::sub-page,QScrollBar::add-line,QScrollBar::sub-line{background: none; border: none;}" )
			logoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			sendLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			settingsLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			walletLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			crLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			createRestoreLabel.setText(cssStyle+"<a href='#' class='hyper-text'>Create or Restore Wallet</a>")
			statLabel.setText(cssStyle+"<a href='#' class='hyper-text'>Node Status</a>")
			waitSpin.setColor(QColor(255,255,255))
		#Light
		elif style==1:
			cssStyle="<style>.amount-text {color: #cc147f} .x-text {color: #26bfb5;} .hyper-text{color:rgba(38,191,181,.9)}</style>"
			stackedWidget.setStyleSheet("QStackedWidget {background-color:#F0F0F0; color:#000000;} QLabel{color:#000000;} QLabel#heading {color: #26bfb5;} QMessageBox,QComboBox,QAbstractItemView {background-color: rgba(255, 255, 255, 1.0); color: #000000;} QLineEdit {background-color: rgba(255, 255, 255, 0.8); color: #000000; border:1px solid #000000;} QPushButton {background-color: #4717F6; background-image: none; color: #FFFFFF;} QPushButton::Hover {background-color: #4114e5;} QTextEdit {background-color: rgba(255, 255, 255, 0.7); color: #000000; border:1px solid #000000;} QScrollBar,QScrollBar::handle {background:rgba(255, 255, 255, 0.7); border:0px solid #000000;} QScrollBar::add-page,QScrollBar::sub-page,QScrollBar::add-line,QScrollBar::sub-line{background: none; border: none;}" )
			logoLabel.setPixmap(xImageBlack.scaledToHeight(45,Qt.SmoothTransformation))
			sendLogoLabel.setPixmap(xImageBlack.scaledToHeight(45,Qt.SmoothTransformation))
			settingsLogoLabel.setPixmap(xImageBlack.scaledToHeight(45,Qt.SmoothTransformation))
			walletLogoLabel.setPixmap(xImageBlack.scaledToHeight(45,Qt.SmoothTransformation))
			crLogoLabel.setPixmap(xImageBlack.scaledToHeight(45,Qt.SmoothTransformation))
			createRestoreLabel.setText(cssStyle+"<a href='#' class='hyper-text'>Create or Restore Wallet</a>")
			statLabel.setText(cssStyle+"<a href='#' class='hyper-text'>Node Status</a>")
			waitSpin.setColor(QColor(71,23,246))
		#Red
		elif style==2:
			cssStyle="<style>.amount-text {color: #FFFFFF;} .x-text {color: #C3073F;} .hyper-text{color:rgba(195,7,63,.5)}</style>"
			stackedWidget.setStyleSheet("QStackedWidget {background-color:#1A1A1D; color: #979A9A;} QLabel{color: #979A9A;} QLabel#heading {color: #950740;} QMessageBox,QComboBox,QAbstractItemView {background-color: rgba(26, 26, 29, 1.0); color: #979A9A;} QLineEdit {background-color: rgba(26, 26, 29, 0.8); color: #979A9A; border:1px solid #000000;} QPushButton {background-color: #6F2232; background-image: none; color: #FFFFFF;} QPushButton::Hover {background-color: #950740;} QTextEdit {background-color: rgba(26, 26, 29, 0.7); color: #979A9A; border:1px solid #000000;} QScrollBar,QScrollBar::handle {background:rgba(26, 26, 29, 0.7); border:0px solid #000000;} QScrollBar::add-page,QScrollBar::sub-page,QScrollBar::add-line,QScrollBar::sub-line{background: none; border: none;}" )
			logoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			sendLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			settingsLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			walletLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			crLogoLabel.setPixmap(xImage.scaledToHeight(45,Qt.SmoothTransformation))
			createRestoreLabel.setText(cssStyle+"<a href='#' class='hyper-text'>Create or Restore Wallet</a>")
			statLabel.setText(cssStyle+"<a href='#' class='hyper-text'>Node Status</a>")
			hLine.setColor(QColor(111,34,50))
			waitSpin.setColor(QColor(149,7,64))

	def clearCRForm():
		crWalletName.clear()
		crWalletPassword.clear()
		crWalletPassphrase.clear()
		crWalletPasswordCheck.clear()
		crWalletPassphraseCheck.clear()
		crMnemonic.clear()

	def crBuildForm(op):
		clearCRForm()
		if op == 0:
			crWalletName.hide()
			crWalletPassword.hide()
			crWalletPassphrase.hide()
			crWalletPasswordCheck.hide()
			crWalletPassphraseCheck.hide()
			crMnemonic.hide()	
			crFormLayout.labelForField(crWalletName).hide()
			crFormLayout.labelForField(crWalletPassword).hide()
			crFormLayout.labelForField(crWalletPassphrase).hide()
			crFormLayout.labelForField(crWalletPasswordCheck).hide()
			crFormLayout.labelForField(crWalletPassphraseCheck).hide()
			crFormLayout.labelForField(crMnemonic).hide()		
		if op == 1:
			crWalletName.show()
			crWalletPassword.show()
			crWalletPassphrase.show()
			crWalletPasswordCheck.show()
			crWalletPassphraseCheck.show()
			crMnemonic.hide()
			crFormLayout.labelForField(crWalletName).show()
			crFormLayout.labelForField(crWalletPassword).show()
			crFormLayout.labelForField(crWalletPassphrase).show()
			crFormLayout.labelForField(crWalletPasswordCheck).show()
			crFormLayout.labelForField(crWalletPassphraseCheck).show()
			crFormLayout.labelForField(crMnemonic).hide()			
		if op == 2:
			crWalletName.show()
			crWalletPassword.show()
			crWalletPassphrase.show()
			crMnemonic.show()
			crWalletPasswordCheck.hide()
			crWalletPassphraseCheck.hide()
			crFormLayout.labelForField(crWalletName).show()
			crFormLayout.labelForField(crWalletPassword).show()
			crFormLayout.labelForField(crWalletPassphrase).show()
			crFormLayout.labelForField(crWalletPasswordCheck).hide()
			crFormLayout.labelForField(crWalletPassphraseCheck).hide()
			crFormLayout.labelForField(crMnemonic).show()

	#Application Setup
	appctxt=ApplicationContext()
	app =appctxt.app

	#Config seteup and Swagger Api settings
	xConfig=configparser.ConfigParser()
	sysPlatform=platform.system().upper()
	baseConfig=appctxt.get_resource('x42lite.ini')
	baseModTime=os.path.getmtime(baseConfig)

	if sysPlatform == 'WINDOWS':
		configDir=os.path.join(os.environ['APPDATA'],'x42lite')
		configPath=os.path.join(configDir,'x42lite.ini')
		if not os.path.exists(configDir):
			os.makedirs(configDir)
			shutil.copyfile(baseConfig,configPath)
		else:
			if not os.path.exists(configPath):
				shutil.copyfile(baseConfig,configPath)
			else:
				configModTime=os.path.getmtime(configPath)
				if baseModTime > configModTime:
					shutil.copyfile(baseConfig,configPath)

	else:
		configPath=baseConfig

	xConfig.read(configPath)
	swagIP=str(xConfig['SETTINGS']['NODE_HOST'])

	swaggerServer = "http://"+swagIP
	historyEndpoint = '/api/Wallet/history'
	balanceEndpoint = '/api/Wallet/balance'
	stakingEndpoint = '/api/Staking/getstakinginfo'
	addressEndpoint = '/api/Wallet/addresses'
	walletEndpoint = '/api/Wallet/files'
	buildTxEndpoint= '/api/Wallet/build-transaction'
	sendTxEndpoint= '/api/Wallet/send-transaction'
	mnemonicEndpoint='/api/Wallet/mnemonic'
	createWalletEndpoint='/api/Wallet/create'
	restoreWalletEndpoint='/api/Wallet/recover'
	nodeStatusEndpoint='/api/Dashboard/Stats'

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
	createRestorePage=QWidget()
	nodeStatusPage=QWidget()
	stackedWidget=QStackedWidget()
	stackedWidget.addWidget(walletPage)
	stackedWidget.addWidget(dashboardPage)
	stackedWidget.addWidget(sendPage)
	stackedWidget.addWidget(settingsPage)
	stackedWidget.addWidget(createRestorePage)
	stackedWidget.addWidget(nodeStatusPage)
	
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
	historyLabel.setObjectName("heading")
	balanceLabel=QLabel()
	balanceLabel.setObjectName("heading")
	addressLabel=QLabel()
	addressLabel.setObjectName("heading")
	stakingLabel=QLabel()
	logoLabel=QLabel()
	sendLogoLabel=QLabel()
	settingsLogoLabel=QLabel()
	walletLogoLabel=QLabel()
	crLogoLabel=QLabel()
	logoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	sendLogoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	settingsLogoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	walletLogoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	crLogoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	autoLabel=QLabel()
	autoLabel.setAlignment(Qt.AlignRight | Qt.AlignCenter)
	xImage=QPixmap(":/base/x42logo.png")
	xImageBlack=QPixmap(":/base/x42logo_black.png")
	xSendIcon=QIcon(":/base/x42logo_send.png")
	xDashboardIcon=QIcon(":/base/x42logo_dashboard.png")
	xSettingsIcon=QIcon(":/base/tune_black.png")
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
	hHistoryLabelLayout=QHBoxLayout()
	hHistoryLabelLayout.addWidget(historyLabel)
	hHistoryLabelLayout.addStretch(1)
	vDashboardLayout.addLayout(hHeaderLayout)
	vDashboardLayout.addLayout(hMidLayout)
	vDashboardLayout.addWidget(hLine)
	vDashboardLayout.addLayout(hHistoryLabelLayout)
	vDashboardLayout.addWidget(walletHistoryArea)
	vDashboardLayout.addLayout(hFooterLayout)
	balanceLabel.setText("<h2>Balances</h2>")
	addressLabel.setText("<h2>Addresses<font color='#979a9a'><small> (click address to copy)</small></font></h2>")
	historyLabel.setText("<h2>Wallet History</h2>")
	dashboardPage.setLayout(vDashboardLayout)

	#wallet select page
	submitWalletButton=QPushButton("GO!")
	submitWalletButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	refreshWalletButton=QPushButton("Refresh")
	refreshWalletButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	clearWalletButton=QPushButton("Close")
	clearWalletButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	settingsButton=QPushButton()
	settingsButton.setIcon(xSettingsIcon)
	settingsButton.setIconSize(QSize(15,15))
	settingsButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	createRestoreLabel=QLabel()
	createRestoreLabel.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
	statLabel=QLabel()
	statLabel.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
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
	selectWalletName.setFixedWidth(250)
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
	hWalletFooterLayout=QHBoxLayout()
	hWalletFooterLayout.addWidget(statLabel)
	hWalletFooterLayout.addStretch(1)
	hWalletFooterLayout.addWidget(createRestoreLabel)
	vWalletLayout.addLayout(hWalletHeaderLayout)
	vWalletLayout.addStretch(1)
	vWalletLayout.addLayout(hWalletFormLayout)
	vWalletLayout.addStretch(1)
	vWalletLayout.addLayout(vWalletFormButtonsLayout)
	vWalletLayout.addStretch(1)
	vWalletLayout.addLayout(hWalletFooterLayout)
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
	selectStyleName=QComboBox()
	selectStyleName.setFixedWidth(200)
	selectStyleName.setEditable(True)
	selectStyleName.lineEdit().setReadOnly(True)
	selectStyleName.lineEdit().setAlignment(Qt.AlignCenter)
	selectStyleName.addItems(['x42-Dark','Light','Red'])
	selectStyleName.setCurrentIndex(int(xConfig['SETTINGS']['THEME']))
	settingsFormLayout.addRow(settingsFormLayout.tr("&Node Address <font color='#979a9a'><small>(IP and Port)</small></font>: "),hostSetting)
	settingsFormLayout.addRow(settingsFormLayout.tr("&Auto Refresh Timer <font color='#979a9a'><small>(In Seconds)</small></font>: "),refreshSetting)
	settingsFormLayout.addRow(settingsFormLayout.tr("&UI Theme: "),selectStyleName)
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

	#Create & Restore Wallet Page 
	submitCRButton=QPushButton("Submit")
	submitCRButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	clearCRButton=QPushButton("Clear")
	clearCRButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	cancelCRButton=QPushButton("Cancel")
	cancelCRButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	hCRFormLayout=QHBoxLayout()
	crFormLayout=QFormLayout()
	crFormLayout.setLabelAlignment(Qt.AlignRight)
	vCRLayout=QVBoxLayout()
	hCRButtonsLayout=QHBoxLayout()
	hCRButtonsLayout.addStretch(1)
	hCRButtonsLayout.addWidget(cancelCRButton)
	hCRButtonsLayout.addWidget(clearCRButton)
	hCRButtonsLayout.addWidget(submitCRButton)
	hCRButtonsLayout.addStretch(1)
	hCRButtonsLayout.setAlignment(Qt.AlignTop)
	regExPword="^\S+$"
	regExPwordValidator=QRegExpValidator(regExPword)
	selectCR=QComboBox()
	selectCR.setFixedWidth(300)
	selectCR.setEditable(True)
	selectCR.lineEdit().setReadOnly(True)
	selectCR.lineEdit().setAlignment(Qt.AlignCenter)
	selectCR.addItems(['Choose Operation','CREATE','RESTORE'])
	crMnemonic=QLineEdit()
	crMnemonic.setFixedWidth(300)
	crMnemonic.setPlaceholderText("word word word ...")
	crWalletName=QLineEdit()
	crWalletName.setFixedWidth(300)
	crWalletName.setPlaceholderText("Enter the Wallets Name")
	crWalletName.setValidator(regExPwordValidator)
	crWalletPassword=QLineEdit()
	crWalletPassword.setFixedWidth(300)
	crWalletPassword.setEchoMode(QLineEdit.Password)
	crWalletPassword.setPlaceholderText("Enter Wallet Password")
	crWalletPassword.setValidator(regExPwordValidator)
	crWalletPassphrase=QLineEdit()
	crWalletPassphrase.setFixedWidth(300)
	crWalletPassphrase.setEchoMode(QLineEdit.Password)
	crWalletPassphrase.setPlaceholderText("Enter Recovery Passphrase")
	crWalletPassphrase.setValidator(regExPwordValidator)
	crWalletPasswordCheck=QLineEdit()
	crWalletPasswordCheck.setFixedWidth(300)
	crWalletPasswordCheck.setEchoMode(QLineEdit.Password)
	crWalletPasswordCheck.setPlaceholderText("Password Check")
	crWalletPassphraseCheck=QLineEdit()
	crWalletPassphraseCheck.setFixedWidth(300)
	crWalletPassphraseCheck.setEchoMode(QLineEdit.Password)
	crWalletPassphraseCheck.setPlaceholderText("Passphrase Check")
	hCRHeaderLayout=QHBoxLayout()
	hCRHeaderLayout.addStretch(1)
	hCRHeaderLayout.addWidget(crLogoLabel)
	hCRHeaderLayout.setAlignment(Qt.AlignTop)
	crFormLayout.addRow(crFormLayout.tr("&Create or Restore Wallet:"),selectCR)
	crFormLayout.addRow(crFormLayout.tr("&Enter Recovery Words:"),crMnemonic)
	crFormLayout.addRow(crFormLayout.tr("&Wallet Name:"),crWalletName)
	crFormLayout.addRow(crFormLayout.tr("&Password:"),crWalletPassword)
	crFormLayout.addRow(crFormLayout.tr("&Passphrase:"),crWalletPassphrase)
	crFormLayout.addRow(crFormLayout.tr("&Re-Enter Password:"),crWalletPasswordCheck)
	crFormLayout.addRow(crFormLayout.tr("&Re-Enter Passphrase:"),crWalletPassphraseCheck)
	crWalletName.hide()
	crWalletPassword.hide()
	crWalletPassphrase.hide()
	crWalletPasswordCheck.hide()
	crWalletPassphraseCheck.hide()
	crMnemonic.hide()
	crFormLayout.labelForField(crWalletName).hide()
	crFormLayout.labelForField(crWalletPassword).hide()
	crFormLayout.labelForField(crWalletPassphrase).hide()
	crFormLayout.labelForField(crWalletPasswordCheck).hide()
	crFormLayout.labelForField(crWalletPassphraseCheck).hide()
	crFormLayout.labelForField(crMnemonic).hide()
	hCRFormLayout.addStretch(1)
	hCRFormLayout.addLayout(crFormLayout)
	hCRFormLayout.addStretch(1)
	hCRFormLayout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
	vCRLayout.addLayout(hCRHeaderLayout)
	vCRLayout.addStretch(1)
	vCRLayout.addLayout(hCRFormLayout)
	vCRLayout.addStretch(1)
	vCRLayout.addLayout(hCRButtonsLayout)
	vCRLayout.addStretch(1)
	createRestorePage.setLayout(vCRLayout)

	#Node Status Page
	statusBackButton=QPushButton("Back")
	statusBackButton.setStyleSheet("max-width: 80px; max-height: 30px;")
	vStatusLayout=QVBoxLayout()
	statusArea=QTextEdit()
	statusArea.setReadOnly(1)
	statusArea.setLineWrapMode(QTextEdit.NoWrap)
	vStatusLayout.addWidget(statusArea)
	vStatusLayout.addWidget(statusBackButton)
	nodeStatusPage.setLayout(vStatusLayout)

	mainWin.addWidget(stackedWidget)

	msgBox=QMessageBox(parent=stackedWidget)
	mainWin.setFixedSize(geom.width()*.5, geom.height() *.6)
	mainWin.show()

	#waiting spinner
	waitSpin=QtWaitingSpinner(mainWin,True,True,Qt.ApplicationModal)
	waitSpin.setColor(QColor(71,23,246))
	waitSpin.setLineWidth(7)

	changeStyle(int(xConfig['SETTINGS']['THEME']))

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
	whichCRSig=workSignal()
	dispCreateSuccessSig=workSignal()
	nodeStatusSig=workSignal()

	loadThread=QThread()
	loadThread.start()
	loadDashboard=backgroundOps()
	loadDashboard.moveToThread(loadThread)
	grabWalletSig.objSig.connect(populateWallets)
	nodeStatusSig.objSig.connect(buildStatusArea)
	nodeStatusSig.workDone.connect(loadDashboard.getNodeStatus)
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
	whichCRSig.objSig.connect(loadDashboard.crWalletWorker)
	dispCreateSuccessSig.strSig.connect(displayCreate)
	dispCreateSuccessSig.workDone.connect(displayRestore)

	refreshTimer=QTimer()
	refreshTimer.timeout.connect(updateTimer)
	refreshTimer.start(1000)

	statusBackButton.clicked.connect(switchToWalletPage)
	clearCRButton.clicked.connect(clearCRForm)
	cancelCRButton.clicked.connect(switchToWalletPage)
	submitCRButton.clicked.connect(createRestoreDecision)
	selectCR.currentIndexChanged.connect(crBuildForm)
	selectStyleName.currentIndexChanged.connect(changeStyle)
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
	createRestoreLabel.linkActivated.connect(switchToCreateRestorePage)
	statLabel.linkActivated.connect(switchToStatusPage)

	walletName=""
	walletParams={}
	rebuildURLs(swagIP)

	app.aboutToQuit.connect(closeThread)
	app.exec_()


