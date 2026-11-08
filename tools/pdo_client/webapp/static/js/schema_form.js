// Forms generated from a JSON Schema: a policy's parameters, a credential's claims.
//
//   var form = window.schemaForm.render(container, schema, values);
//   form.value()   -> the object the fields describe; empty optional fields are left out
//   form.errors()  -> ["<field> is required", ...] for what is missing
//
// Strings, numbers, booleans, nested objects, enums and lists of strings get
// fields of their own; anything else is edited as JSON. The server validates the
// result against the full schema again.

(function () {
    var counter = 0;

    function nextId() {
        counter += 1;
        return 'schema-field-' + counter;
    }

    function humanize(key) {
        var words = String(key)
            .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
            .replace(/[_-]+/g, ' ')
            .toLowerCase();
        return words.charAt(0).toUpperCase() + words.slice(1);
    }

    function group(schema, key, required, input) {
        var node = document.createElement('div');
        node.className = 'form-group';
        node.dataset.field = key;
        var label = document.createElement('label');
        label.setAttribute('for', input.id);
        label.textContent = (schema.title || humanize(key)) + (required ? '' : ' (optional)');
        node.appendChild(label);
        node.appendChild(input);
        if (schema.description) {
            var hint = document.createElement('small');
            hint.textContent = schema.description;
            node.appendChild(hint);
        }
        return node;
    }

    function present(value) {
        return [value, value !== '' && value !== undefined];
    }

    // Each field is {node, read() -> [value, present], errors(name) -> [...]}.
    function field(schema, key, value, required) {
        schema = schema || {};
        var items = schema.items || {};
        var input;

        if (schema.type === 'object' && schema.properties) {
            var box = document.createElement('fieldset');
            box.className = 'schema-fieldset';
            box.dataset.field = key;
            var legend = document.createElement('legend');
            legend.textContent = (schema.title || humanize(key)) + (required ? '' : ' (optional)');
            box.appendChild(legend);
            var inner = object(box, schema, value || {});
            return {
                node: box,
                read: function () {
                    var v = inner.read();
                    return [v, Object.keys(v).length > 0];
                },
                errors: inner.errors,
            };
        }

        if (schema.type === 'boolean') {
            input = document.createElement('input');
            input.type = 'checkbox';
            input.id = nextId();
            input.checked = value === true;
            var node = document.createElement('div');
            node.className = 'form-group';
            node.dataset.field = key;
            var wrap = document.createElement('label');
            wrap.className = 'checkbox-item';
            wrap.setAttribute('for', input.id);
            wrap.appendChild(input);
            var span = document.createElement('span');
            span.textContent = schema.title || humanize(key);
            wrap.appendChild(span);
            node.appendChild(wrap);
            return { node: node, read: function () { return [input.checked, true]; } };
        }

        if (schema.type === 'array' && items.enum) {
            var list = document.createElement('div');
            list.className = 'checkbox-list';
            list.id = nextId();
            items.enum.forEach(function (option) {
                var label = document.createElement('label');
                label.className = 'checkbox-item';
                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = option;
                cb.checked = (value || []).indexOf(option) !== -1;
                label.appendChild(cb);
                label.appendChild(document.createTextNode(' ' + option));
                list.appendChild(label);
            });
            return {
                node: group(schema, key, required, list),
                read: function () {
                    var chosen = Array.from(list.querySelectorAll('input:checked')).map(function (cb) {
                        return cb.value;
                    });
                    return [chosen, chosen.length > 0];
                },
            };
        }

        if (schema.type === 'array' && items.type === 'string') {
            input = document.createElement('textarea');
            input.id = nextId();
            input.rows = 3;
            input.placeholder = 'One per line';
            input.value = (value || []).join('\n');
            return {
                node: group(schema, key, required, input),
                read: function () {
                    var lines = input.value.split('\n').map(function (l) { return l.trim(); })
                        .filter(function (l) { return l; });
                    return [lines, lines.length > 0];
                },
            };
        }

        if (schema.type === 'string' && schema.enum) {
            input = document.createElement('select');
            input.id = nextId();
            input.appendChild(new Option(required ? 'Choose…' : '—', ''));
            schema.enum.forEach(function (option) {
                input.appendChild(new Option(option, option, false, option === value));
            });
            return {
                node: group(schema, key, required, input),
                read: function () { return present(input.value); },
            };
        }

        if (schema.type === 'string') {
            input = document.createElement('input');
            input.type = schema.format === 'email' ? 'email' : 'text';
            input.id = nextId();
            input.value = value == null ? '' : value;
            if (schema.format === 'date-time') input.placeholder = '2027-01-01T00:00:00Z';
            return {
                node: group(schema, key, required, input),
                read: function () { return present(input.value.trim()); },
            };
        }

        if (schema.type === 'integer' || schema.type === 'number') {
            input = document.createElement('input');
            input.type = 'number';
            input.id = nextId();
            if (schema.type === 'integer') input.step = '1';
            input.value = value == null ? '' : value;
            return {
                node: group(schema, key, required, input),
                read: function () {
                    return input.value === '' ? [undefined, false] : [Number(input.value), true];
                },
            };
        }

        input = document.createElement('textarea');
        input.id = nextId();
        input.className = 'mono';
        input.rows = 4;
        input.value = value === undefined ? '' : JSON.stringify(value, null, 2);
        return {
            node: group(schema, key, required, input),
            read: function () {
                if (!input.value.trim()) return [undefined, false];
                try {
                    return [JSON.parse(input.value), true];
                } catch (e) {
                    return [input.value, true];
                }
            },
            errors: function (name) {
                if (!input.value.trim()) return [];
                try {
                    JSON.parse(input.value);
                    return [];
                } catch (e) {
                    return [name + ' is not valid JSON'];
                }
            },
        };
    }

    function object(container, schema, values) {
        var required = schema.required || [];
        var fields = Object.keys(schema.properties || {}).map(function (key) {
            var isRequired = required.indexOf(key) !== -1;
            var f = field(schema.properties[key], key, values[key], isRequired);
            container.appendChild(f.node);
            return { key: key, field: f, required: isRequired };
        });
        return {
            read: function () {
                var out = {};
                fields.forEach(function (f) {
                    var r = f.field.read();
                    if (r[1]) out[f.key] = r[0];
                });
                return out;
            },
            errors: function (prefix) {
                var errors = [];
                fields.forEach(function (f) {
                    var name = (prefix ? prefix + '.' : '') + f.key;
                    var r = f.field.read();
                    if (f.required && !r[1]) {
                        errors.push(name + ' is required');
                    } else if (r[1] && f.field.errors) {
                        errors = errors.concat(f.field.errors(name));
                    }
                });
                return errors;
            },
        };
    }

    function render(container, schema, values) {
        container.innerHTML = '';
        schema = schema || {};
        if (!Object.keys(schema.properties || {}).length) {
            var none = document.createElement('p');
            none.className = 'muted';
            none.textContent = 'Nothing to fill in.';
            container.appendChild(none);
        }
        var form = object(container, schema, values || {});
        return {
            value: form.read,
            errors: function () { return form.errors(''); },
        };
    }

    window.schemaForm = { render: render };
})();
