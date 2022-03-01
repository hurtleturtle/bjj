def gen_form_item(item_id=None, name=None, placeholder=None,
                  required=False, item_type='text', autocomplete='off',
                  field_type='input', label='', options={}, value='',
                  selected_option='', item_class='', label_class='',
                  field_class='', href='', multiple=False, rows=10, columns=80, 
                  textarea_text=None, extra_attrs=None):
    item = {
        'id': item_id,
        'name': name if name else item_id,
        'item_class': item_class,
        'label_class': label_class,
        'field_class': field_class,
        'placeholder': placeholder if placeholder else '',
        'required': required,
        'type': item_type,
        'value': value,
        'autocomplete': autocomplete,
        'field_type': field_type,
        'label': label,
        'options': options,
        'selected_option': selected_option,
        'href': href,
        'multiple': multiple,
        'rows': rows if rows else 10,
        'columns': columns if columns else 120,
        'textarea_text': textarea_text,
        'extra_attrs': extra_attrs
    }

    return item


def gen_options(options, values=[]):
    option_dict = {}
    for idx, opt in enumerate(options):
        if values:
            option_dict[opt] = {
                'value': values[idx],
                'text': opt
            }
        else:
            option_dict[opt] = {
                'value': opt,
                'text': opt
            }

    return option_dict
