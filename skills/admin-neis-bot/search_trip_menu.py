import io
import os
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.environ['no_proxy'] = 'localhost,127.0.0.1'

opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

# Check if neis tab is already open
neis_handle = None
for h in driver.window_handles:
    driver.switch_to.window(h)
    if 'neis.go.kr' in driver.current_url:
        neis_handle = h
        print('Found existing NEIS tab:', driver.title)
        break

if not neis_handle:
    # Open via SSO
    for h in driver.window_handles:
        driver.switch_to.window(h)
        if 'eduptl' in driver.current_url:
            sso_url = driver.execute_script("""
                var btn = document.querySelector('a.menuBtn[id*="neis"]');
                return btn ? btn.id : null;
            """)
            if sso_url:
                print('Opening SSO URL:', sso_url)
                driver.switch_to.new_window('tab')
                driver.get(sso_url)
                time.sleep(6)
                neis_handle = driver.current_window_handle
                break

if neis_handle:
    driver.switch_to.window(neis_handle)
    print('Current NEIS URL:', driver.current_url)
    
    js = """
        var results = [];
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        for (var i = 0; i < apps.length; i++) {
            var app = apps[i];
            var dmList = ['dsBaseMenu', 'dsMenu', 'ds_menu', 'dsAllMenu'];
            for (var d = 0; d < dmList.length; d++) {
                var dm = app.lookup(dmList[d]);
                if (dm && dm.getRowDataRanged) {
                    var rows = dm.getRowDataRanged();
                    for (var r = 0; r < rows.length; r++) {
                        var row = rows[r];
                        var str = JSON.stringify(row);
                        if (str.indexOf('출장') !== -1 || str.indexOf('근무상황') !== -1 || str.indexOf('복무') !== -1) {
                            results.push({appId: app.app ? app.app.id : '', dm: dmList[d], row: row});
                        }
                    }
                }
            }
        }
        return results;
    """
    res = driver.execute_script(js)
    print(f'Matching menus count: {len(res)}')
    for r in res:
        print(json.dumps(r, ensure_ascii=False))
else:
    print('Failed to find or open NEIS')
