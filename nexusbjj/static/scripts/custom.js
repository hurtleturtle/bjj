const toggleRow = (elementId) => {
    elementIdToToggle = 'collapsed-row-' + elementId
    elementIdWithButton = 'toggle-' + elementId
    document.getElementById(elementIdToToggle).classList.toggle('hide-row');
    button = document.getElementById(elementIdWithButton)

    if (button.innerHTML == '+') {
        button.innerHTML = '&ndash;'
    } else {
        button.innerHTML = '+'
    }
}