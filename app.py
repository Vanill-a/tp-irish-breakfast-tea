import os
import cliniko.api
import json
import stock
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


def main():
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()


# Events
@app.event("app_home_opened")
def handle_app_home_opened(ack, event, client, logger):
    ack()
    strUserId = event["user"]
    print("App Home Opened by " + strUserId)

    with open("views\\home.json", "r") as f:
        objView = json.load(f)

    objResult = client.views_publish(user_id=strUserId, view=objView)
    logger.info(objResult)
    return


# Views
@app.view("submit_transfer_stock")
def handle_submit_transfer_stock(ack, body, client, view, logger):
    strUserId = body["user"]["id"]
    ack()

    # Retrieve product id
    objProductId = view["blocks"][0]["elements"]
    strProductId = objProductId[0]["text"]

    # Retrieve object states
    objViewStateVals = view["state"]["values"]
    objStockSource = objViewStateVals["block_source"]["select_clinic_source"]
    objStockDestination = objViewStateVals["block_target"]["select_clinic_target"]
    objStockAmount = objViewStateVals["block_amount"]["text_transfer_amount"]

    # Retrieve values of objects
    strSourceClinic = objStockSource["selected_option"]["value"]
    strTargetClinic = objStockDestination["selected_option"]["value"]
    strAmountVal = objStockAmount["value"]
    intAmountVal = int(strAmountVal)

    # Get current stock levels
    objStock = stock.get_stock(strProductId)
    intCurrSourceVal = objStock[strSourceClinic]
    intCurrTargetVal = objStock[strTargetClinic]

    if intAmountVal > intCurrSourceVal:
        return
    
    # Adjust Stock Levels
    intNewSourceVal = intCurrSourceVal - intAmountVal
    intNewTargetVal = intCurrTargetVal + intAmountVal
    objStock[strSourceClinic] = intNewSourceVal
    objStock[strTargetClinic] = intNewTargetVal

    # Push changes
    objNewStock = stock.transfer_stock(
        strProductId,
        strSourceClinic,
        strTargetClinic,
        intAmountVal,
        objStock)
    update_home(strUserId, client, logger, objNewStock)
    return


@app.view("submit_adjust_stock")
def handle_submit_adjust_stock(ack, body, client, view, logger):
    ack()
    strUserId = body["user"]["id"]
    
    dicAdjustmentSign = {
        "Stock Purchase": 1,
        "Returned": 1,
        "Damaged": -1,
        "Out of Date": -1,
        "Correction": -1
    }

    # Retrieve product id
    objProductId = view["blocks"][0]["elements"]
    strProductId = objProductId[0]["text"]
    
    # Retrieve object states / values
    objViewStateVals = view["state"]["values"]
    objAdjustmentType = objViewStateVals["block_type"]["select_adjustment_type"]
    objTargetClinic = objViewStateVals["block_target"]["select_clinic_target"]
    objAmount = objViewStateVals["block_amount"]["text_amount"]
    strAdjustmentVal = objAdjustmentType["selected_option"]["value"]
    strTargetVal = objTargetClinic["selected_option"]["value"]
    strAmountVal = objAmount["value"]
    intAmountVal = int(strAmountVal) * dicAdjustmentSign[strAdjustmentVal]
    objStock = stock.get_stock(strProductId)
    
    # Do nothing if reduction exceeds current total
    if intAmountVal < 0:
        intCurrAmount = objStock[strTargetVal]
        if intCurrAmount < intAmountVal:
            return
    
    # Adjust stock level for selected clinic
    objStock[strTargetVal] += intAmountVal
    objNewStock = stock.adjust_stock(strProductId, strAdjustmentVal, strTargetVal, intAmountVal, objStock)
    update_home(strUserId, client, logger, objNewStock)
    return


# Actions
@app.action("select_product")
def handle_select_product(ack, body, client, logger):
    strUserId = body["user"]["id"]
    ack()
    print("Product selected by User: " + strUserId)

    # Get product Id
    objActions = body["actions"]
    objSelectProduct = objActions[0]
    objSelectedOption = objSelectProduct["selected_option"]
    objOptionValue = objSelectedOption["value"]
    strProductId = str(objOptionValue)
    print("Selected product: " + strProductId)

    objStock = stock.get_stock(strProductId)
    update_home(strUserId, client, logger, objStock)
    return

@app.action("button_transfer_stock")
def handle_button_transfer_stock(ack, body, client, logger):
    ack()

    with open("views\\transfer.json", "r") as f:
        objView = json.load(f)

    button_open_modal(body, client, logger, objView)
    return


@app.action("button_adjust_stock")
def handle_button_adjust_stock(ack, body, client, logger):
    ack()

    with open("views\\adjust.json", "r") as f:
        objView = json.load(f)

    button_open_modal(body, client, logger, objView)
    return


@app.action("button_sync_stock")
def handle_button_sync_stock(ack, body, client, logger):
    return


# Options
@app.options("select_product")
def handle_select_product_query(ack, payload):
    # Get product list from Cliniko
    print("Searching Cliniko products...")
    strFilter = "?q=name:~" + payload["value"]
    strQuery = "products" + strFilter
    objProductList = cliniko.api.get_data("products", strQuery)
    print(str(len(objProductList)) + " product(s) found")
    
    # Create select options from list
    objOptionList = []
    for a in objProductList:
        objNewOption = {
            "value": a["id"],
            "text": {
                "type": "plain_text",
                "text": a["name"],
                "emoji": True
            }
        }
        objOptionList.append(objNewOption)
        
    ack(options=objOptionList)
    return


# Common Functions
def update_home(user_id, client, logger, stock_data):
    strSlackTotal = str(stock.get_total(stock_data))
    strClinikoTotal = str(stock_data["ClinikoTotal"])

    print("Updating home view...")
    with open("views\\home.json", "r") as f:
        objView = json.load(f)
    
    # Set new field totals
    objBlocks = objView["blocks"]
    objClinics = objBlocks[5]["fields"]
    objBlocks[2]["text"]["text"] += stock_data["Notes"]
    objClinics[1]["text"] = str(stock_data["Bellbowrie"])
    objClinics[3]["text"] = str(stock_data["Kenmore"])
    objClinics[5]["text"] = str(stock_data["Karalee"])
    objBlocks[7]["fields"][1]["text"] = f"{strSlackTotal} ({strClinikoTotal})"

    # Push changes
    objResult = client.views_publish(user_id=user_id, view=objView)
    print("Home view updated!")
    logger.info(objResult)
    return


def button_open_modal(body, client, logger, view):
    # Get selected product id
    objViewStateVals = body["view"]["state"]["values"]
    objProductSelect = objViewStateVals["secProductSelect"]["select_product"]
    objSelectedOption = objProductSelect["selected_option"]
    intOptionVal = objSelectedOption["value"]
    
    # Populate modal with product id and open
    view["blocks"][0]["elements"][0]["text"] = intOptionVal
    objResult = client.views_open(trigger_id=body["trigger_id"], view=view)
    logger.info(objResult)
    return


if __name__ == "__main__":
    main()