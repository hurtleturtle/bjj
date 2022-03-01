window.onload = function() {
    fill_browser_cookies_into_table();
}

function fill_browser_cookies_into_table(params) {
    var browser_cookie_cells = document.querySelectorAll("td.browser-cookie");
    var cookies = document.cookie.split('&');
    var cookie_dict = {};

    for (idx in cookies) {
        cookie = cookies[idx].split('=');
        cookie_dict[cookie[0]] = cookie[1];
    }
        

    for (cell_idx in browser_cookie_cells) {
        cell = browser_cookie_cells[cell_idx];
        cell_cookie = cell.id;
        browser_cookie_value = cookie_dict[cell_cookie];

        if (browser_cookie_value) {
            cell.innerHTML = browser_cookie_value;
        }
        else {
            cell.innerHTML = 'Cookie inaccessible with JavaScript';
        }
    }
}
