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

async function confirmCheckIn(attendance_record_id, coach_id, element) {
    try {
        response = await axios.get('/api/attendance/confirm-check-in?attendance_record_id=' + attendance_record_id
                                   + '&coach_id=' + coach_id);
        console.log(response)

        if (response.data['result'] == 'success') {
            element.classList.toggle('checked-in')
        }
    }
    catch (error) {
        console.log(error)
    }
}

async function checkIn(class_id, child_id) {
    if (typeof(class_id) === 'undefined') class_id = 'all';
    if (typeof(child_id) === 'undefined') child_id = false;

    try {
        const url = '/api/attendance/check-in?class_id=' + class_id;
        
        if (child_id) {
            url += '&child_id=' + child_id;
        }

        const response = await axios.get(url);
        console.log(response);

        let all_classes_attended = true;

        // TODO: handle response and switch colours of elements
        for (let i = 0; i < response.data.length; i++) {
            const class_data = response.data[i];
            const anchor_element = document.getElementById('class-' + class_data['id']);
            const class_name_text = anchor_element.getElementsByTagName('h2')[0]
            const attendance = class_data['attendance']
            all_classes_attended = (all_classes_attended && attendance)

            if (attendance) {
                anchor_element.classList.add('checked-in')
                class_name_text.textContent = class_data['class_name'] + "(Checked In)"
            }
            else {
                anchor_element.classList.remove('checked-in')
                class_name_text.textContent = class_data['class_name']
            }
        }

        const all_anchor = document.getElementById('class-all')
        if (all_classes_attended) {
            all_anchor.classList.add('checked-in')
        }
        else {
            all_anchor.classList.remove('checked-in')
        }
    }
    catch (error) {
        console.log(error)
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