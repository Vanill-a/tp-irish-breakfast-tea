import json
import cliniko.api

def get_stock(product_id):
    strQuery = "products/" + product_id
    objProduct = cliniko.api.get_data_item(strQuery)
    objOutput = get_dict(objProduct)
    return objOutput


def transfer_stock(product_id, source, target, amount, new_stock):
    # Create stock adjustments
    # Source adjustment
    strComment = "Transfer From " + source
    create_stock_adjustment(product_id, "Other", amount * -1, strComment)
    # Target adjustment
    strComment = "Transfer To " + target
    create_stock_adjustment(product_id, "Other", amount, strComment)

    # Push changes to stock totals
    objOutput = set_stock(product_id, new_stock)
    return objOutput


def adjust_stock(product_id, adjustment_type, target, amount, new_stock):
    strComment = "Adjustment at " + target
    create_stock_adjustment(product_id, adjustment_type, amount, strComment)
    objOutput = set_stock(product_id, new_stock)    
    return objOutput


def create_stock_adjustment(product_id, adjustment_type, amount, comment):
    strQuery = "stock_adjustments"
    objData = {
        "product_id": product_id,
        "quantity": amount,
        "adjustment_type": adjustment_type,
        "comment": comment
    }
    # TODO Uncomment for rollout
    cliniko.api.post_data_item(strQuery, objData)
    return


def set_stock(product_id, stock):
    strQuery = "products/" + product_id
    stock.pop("ClinikoTotal")
    strNotes = json.dumps(stock)
    objData = { "notes": strNotes }
    objProduct = cliniko.api.put_data_item(strQuery, objData)
    objOutput = get_dict(objProduct)
    return objOutput


def sync_stock_all(last_sync):
    strQuery = ("invoice_items"
        + "?q=created_at:>" + last_sync)
    arrInvoiceItems = cliniko.api.get_data("invoice_items", strQuery)
    dicChangeLog = {}
    dicClinics = {}

    for a in arrInvoiceItems:
        # Skip non-product and deleted invoice items
        if "product" not in a:
            continue
        if a["deleted_at"] is not None:
            continue

        intQuantity = a["quantity"]
        strInvoiceLink = a["invoice"]["links"]["self"]
        strProductLink = a["product"]["links"]["self"]
        strProductId = strProductLink.split("product/").pop()
        
        dicInvoice = cliniko.api.get_request_data(strInvoiceLink)
        strBusinessLink = dicInvoice["business"]["links"]["self"]
        strBusinessId = strBusinessLink.split("business/").pop()

        if strBusinessId not in dicClinics:
            dicBusiness = cliniko.api.get_request_data(strBusinessLink)
            strBusinessName = dicBusiness["business_name"]
            strClinicName = strBusinessName.split("Target Physio ").pop()
            dicClinics[strBusinessId] = strClinicName

        if strProductId not in dicChangeLog:
            dicProduct = get_stock(strProductId)
            dicChangeLog[strProductId] = dicProduct

        strClinic = dicClinics[strBusinessId]
        dicProduct = dicChangeLog[strProductId]
        dicProduct[strClinic] -= intQuantity

    for k, v in dicChangeLog.items():
        set_stock(k, v)

    return


def sync_stock_product(product_id, stock):
    # Get stock adjustments since last sync
    strQuery = ("stock_adjustments"
        + "?q[]=product_id:=" + product_id
        + "&q[]=created_at:>" + stock["Synced"])
    objAdjustments = cliniko.api.get_data("stock_adjustments", strQuery)

    # Find invoice items for each
    for a in objAdjustments:
        # Filter out any non-sold adjustment type
        if a["adjustment_type"] != "Item Sold" and a["adjustment_type"] != "Returned":
            continue

        objInvoiceItem = get_invoice_item(a["updated_at"]) # What if null?
        strProductId = objInvoiceItem["product"]["links"]["self"]

        if strProductId != product_id:
            # Throw exception
            return
        
        strInvoiceURL = objInvoiceItem["invoice"]["links"]["self"]
        objInvoice = cliniko.api.get_request_data(strInvoiceURL)
        strClinicURL = objInvoice["business"]["links"]["self"]
        objClinic = cliniko.api.get_request_data(strClinicURL)
        strClinicName = objClinic["business_name"]
        strShortName = strClinicName # TODO split off "Target Physio"

        # Track changes to clinic total
    
    # Update sync time
    stock["Synced"]
    return


def get_total(stock):
    return stock["Bellbowrie"] + stock["Kenmore"] + stock["Karalee"]


def get_dict(product):
    strNotes = product["notes"]
    intStockLevel = product["stock_level"]
    objOutput = json.loads(strNotes)
    objOutput["ClinikoTotal"] = intStockLevel
    return objOutput


def get_invoice_item(updated_at):
    strQuery = ("invoice_items"
        + "?q=updated_at:=" + updated_at)
    objOutput = cliniko.api.get_data("invoice_items", strQuery)
    return objOutput


def create_stock_report():
    strQuery = "products"
    objProductList = cliniko.api.get_data("products", strQuery)
    
    return