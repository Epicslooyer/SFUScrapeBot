from playwright.sync_api import sync_playwright
import time

def automate_sfu(username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto('https://go.sfu.ca')

        page.click('input[name="btnSubmit"]')

        page.fill('#username', username)

        page.fill('#password', password)

        page.click('input[name="submit"]')

        if page.is_visible('#code'):

            auth_code = input("Please enter your 6-digit authentication code: ")
            page.fill('#code', auth_code)
            
            page.check('input[type="checkbox"].hidden')
            
            page.click('button.ui.primary.button')

        page.wait_for_load_state('networkidle')

        page.wait_for_load_state('networkidle')
        
        print("Waiting for Student Centre button...")
        try:
            student_centre = None
            selectors = [
                '#win0divPTNUI_LAND_REC_GROUPLET\\$0',
                'text=Student Centre',                   
                'a:has-text("Student Centre")'          
            ]
            
            for selector in selectors:
                try:
                    student_centre = page.wait_for_selector(
                        selector,
                        state='visible',
                        timeout=20000
                    )
                    if student_centre:
                        print(f"Found Student Centre button using selector: {selector}")
                        break
                except:
                    continue
            
            if student_centre:
                student_centre.click()
                print("Clicked Student Centre button")
            else:
   
                print("Trying JavaScript click...")
                page.evaluate('''
                    const links = Array.from(document.querySelectorAll('a'));
                    const studentCentreLink = links.find(a => a.textContent.includes('Student Centre'));
                    if (studentCentreLink) studentCentreLink.click();
                ''')
            
        except Exception as e:
            print(f"Error clicking Student Centre: {str(e)}")
            current_url = page.url
            print("Current URL:", current_url)
            page.screenshot(path="error_screenshot.png")
            links = page.query_selector_all('a')
            link_texts = [link.text_content() for link in links]
            print("Available links:", link_texts)
            raise

        page.click('#win0divPTNUI_LAND_REC_GROUPLET\\$0')
        page.wait_for_load_state('networkidle')
        
        page.wait_for_selector('#DERIVED_SSS_SCR_SSS_LINK_ANCHOR3', state='visible', timeout=60000)
        
        try:
            page.click('#DERIVED_SSS_SCR_SSS_LINK_ANCHOR3')
        except:
            page.evaluate('document.querySelector("#DERIVED_SSS_SCR_SSS_LINK_ANCHOR3").click()')
        page.wait_for_load_state('networkidle')

        page.click('#SSR_DUMMY_RECV1\\$sels\\$1\\$\\$0')
        page.click('#DERIVED_SSS_SCT_SSR_PB_GO')

        page.click('#DERIVED_REGFRM1_SSR_CLS_SRCH_TYPE\\$249\\$')
        page.click('#DERIVED_REGFRM1_SSR_PB_SRCH')

        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    username = input("Enter your SFU username: ")
    password = input("Enter your SFU password: ")
    
    automate_sfu(username, password)