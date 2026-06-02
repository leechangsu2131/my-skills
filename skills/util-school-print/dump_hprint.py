import win32com.client

def probe_hprint():
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        hwp.XHwpWindows.Item(0).Visible = False
        act = hwp.CreateAction("Print")
        hset = act.CreateSet()
        act.GetDefault(hset)
        
        candidates = [
            "PaperBin", "PrinterPaperSource", "PrinterDefaultSource", 
            "Tray", "PaperTray", "PaperSource", "Bin", "PrinterBin",
            "DevMode", "DEVMODE", "DefaultSource", "dmDefaultSource"
        ]
        
        print("Probing candidates...")
        for c in candidates:
            try:
                # To check if parameter exists, we try to set it to a valid int or string
                hset.SetItem(c, 1)
                print(f"FOUND: {c}")
            except Exception:
                pass
                
        hwp.Quit()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe_hprint()
