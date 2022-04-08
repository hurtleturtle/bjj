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

function toggleAngle(element) {
    icon = element.lastElementChild
    icon.classList.toggle('fa-chevron-right')
    icon.classList.toggle('fa-chevron-down')
}

function expand(anchors, content_divs) {
    anchor_elements = document.querySelectorAll(anchors)
    content_elements = document.querySelectorAll(content_divs)
    i = 0

    anchor_elements.forEach(element => {
        element.classList.remove("collapsed")
        element.setAttribute("aria-expanded", "true")

        content = content_elements[i]
        content.classList.add("show")
        
        icon = element.lastElementChild
        icon.classList.add('fa-chevron-down')
        icon.classList.remove('fa-chevron-right')
        i += 1
    });
}

function collapse(anchors, content_divs) {
    anchor_elements = document.querySelectorAll(anchors)
    content_elements = document.querySelectorAll(content_divs)
    i = 0

    anchor_elements.forEach(element => {
        element.classList.add("collapsed")
        element.setAttribute("aria-expanded", "false")

        content = content_elements[i]
        content.classList.remove("show")
        
        icon = element.lastElementChild
        icon.classList.remove('fa-chevron-down')
        icon.classList.add('fa-chevron-right')
        i += 1
    });
}