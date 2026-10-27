local inventory = {} -- sphinx inventories
local autolink       -- set in Meta
local autolink_ignore_token = "qd-no-link"

local function _debug_log(text, debug)
    if debug then
        quarto.log.warning(text)
    end
end

local function read_file(filename, mode)
    local file = io.open(filename, mode or "r")
    if file == nil then
        return nil
    end
    local str = file:read("a")
    file:close()
    return str
end

local function parse_inv_text(str)
    local project = str:match("# Project: (%S+)")
    local version = str:match("# Version: (%S+)")

    local data = { project = project, version = version, items = {} }

    local ptn_data =
        "^" ..
        "(.-)%s+" ..     -- name
        "([%S:]-):" ..   -- domain
        "([%S]+)%s+" ..  -- role
        "(%-?%d+)%s+" .. -- priority
        "(%S*)%s+" ..    -- uri
        "(.-)\r?$"       -- dispname


    -- Iterate through each line in the file content
    for line in str:gmatch("[^\r\n]+") do
        if not line:match("^#") then
            -- Match each line against the pattern
            local name, domain, role, priority, uri, dispName = line:match(ptn_data)

            -- if name is nil, raise an error
            if name == nil then
                error("Error parsing line: " .. line)
            end

            data.items[#data.items + 1] = {
                name = name,
                domain = domain,
                role = role,
                priority = priority,
                uri = uri,
                dispName = dispName
            }
        end
    end
    return data
end

local function decode_json(str)
    -- pandoc's native decoder is much faster than quarto.json for large inventories
    if pandoc.json then
        return pandoc.json.decode(str, false)
    end
    return quarto.json.decode(str)
end

-- The merged inventory, as name -> flat list of (domain, role, prefix index,
-- uri) rows, plus the uri prefixes. Decoding every inventory (and expanding
-- aliases) takes most of a second for large ones, so the result is cached as
-- Lua bytecode in the project's .quarto dir, keyed by the inventory contents.
local rows_by_name = {}
local prefixes = {}
local items_by_name = {} -- items materialized from rows, by name

local function items_for(name)
    local items = items_by_name[name]
    if items == nil then
        items = {}
        local rows = rows_by_name[name]
        if rows ~= nil then
            for i = 1, #rows, 4 do
                items[#items + 1] = {
                    name = name,
                    domain = rows[i] or nil,
                    role = rows[i + 1] or nil,
                    uri = prefixes[rows[i + 2]] .. rows[i + 3],
                }
            end
        end
        items_by_name[name] = items
    end
    return items
end

-- each inventory has entries: project, version, items
local function lookup(search_object, debug)
    local results = {}
    if search_object.name == nil then
        return nil
    end
    do
        for _, item in ipairs(items_for(search_object.name)) do
            -- e.g. :external+<inv_name>:<domain>:<role>:`<name>`
            if item.inv_name and item.inv_name ~= search_object.inv_name then
                goto continue
            end

            if item.name ~= search_object.name then
                goto continue
            end

            if search_object.role and item.role ~= search_object.role then
                goto continue
            end

            if search_object.domain and item.domain ~= search_object.domain then
                goto continue
            else
                if search_object.domain or item.domain == "py" then
                    table.insert(results, item)
                end

                goto continue
            end

            ::continue::
        end
    end

    if #results == 1 then
        return results[1]
    end
    if #results > 1 then
        _debug_log("Found multiple matches for " .. search_object.name .. ", using the first match.", debug)
        return results[1]
    end
    if #results == 0 then
        _debug_log("Found no matches for object:\n", debug)
        _debug_log(search_object, debug)
    end

    return nil
end

local function mysplit(inputstr, sep)
    if sep == nil then
        sep = "%s"
    end
    local t = {}
    for str in string.gmatch(inputstr, "([^" .. sep .. "]+)") do
        table.insert(t, str)
    end
    return t
end

local function normalize_role(role)
    if role == "func" then
        return "function"
    end
    return role
end

local function copy_replace(original, key, new_value)
    -- First create a copy of the table
    local copy = {}
    for k, v in pairs(original) do
        copy[k] = v
    end

    -- Then replace the specific value
    copy[key] = new_value

    return copy
end

local function contains(list, value)
    -- check if list contains a value
    for i, v in ipairs(list) do
        if v == value then
            return true
        end
    end
    return false
end

local function flatten_alias_list(list)
    -- flatten a list of lists into a single list,
    -- where each entry has the form {key, subvalue}}
    -- e.g.
    --   input: {key1 = {subval1, subval2}, key2 = subval3}
    --   output: {{key1, subval1}, {key1, subval2}, {key2, subval3}}
    local flat = {}
    for key, sublist in pairs(list) do
        if type(sublist) == "table" then
            for _, subvalue in ipairs(sublist) do
                table.insert(flat, { key, subvalue })
            end
        else
            table.insert(flat, { key, sublist })
        end
    end
    return flat
end

local function alias_prefix(alias)
    if not alias or pandoc.utils.stringify(alias) == "" then
        return ""
    end
    -- TODO: ensure alias doesn't end with period
    return pandoc.utils.stringify(alias) .. "."
end

local function prepend_aliases(flat_aliases)
    -- if str up to first period starts with an alias, then
    -- replace it with the full name.
    -- For example, suppose we have the alias quartodoc -> qd
    -- e.g. qd.Auto -> quartodoc.Auto
    -- e.g. qda.Auto -> qda.Auto

    local new_inv = {}
    new_inv["project"] = "aliases"
    new_inv["version"] = "0.0.9999" -- I have not begun to think about version...
    new_inv["items"] = {}

    for _, name_pair in pairs(flat_aliases) do
        local full = name_pair[1]
        local full_prefix = full .. "."
        local prefix = alias_prefix(name_pair[2])
        for _, inv in ipairs(inventory) do
            for _, item in ipairs(inv.items) do
                if string.find(item.name, full_prefix, 1, true) == 1 then
                    -- replace full .. "." with alias .. "."
                    local new_name = prefix .. string.sub(item.name, string.len(full) + 2)
                    table.insert(new_inv.items, copy_replace(item, "name", new_name))
                end
            end
        end
    end
    table.insert(inventory, new_inv)
end

local function build_search_object(str, debug)
    local starts_with_colon = str:sub(1, 1) == ":"
    local search = {}
    if starts_with_colon then
        local t = mysplit(str, ":")
        if #t == 2 then
            -- e.g. :py:func:`my_func`
            search.role = normalize_role(t[1])
            search.name = t[2]:match("%%60(.*)%%60")
        elseif #t == 3 then
            -- e.g. :py:func:`my_func`
            search.domain = t[1]
            search.role = normalize_role(t[2])
            search.name = t[3]:match("%%60(.*)%%60")
        elseif #t == 4 then
            -- e.g. :ext+inv:py:func:`my_func`
            search.external = true

            search.inv_name = t[1]:match("external%+(.*)")
            search.domain = t[2]
            search.role = normalize_role(t[3])
            search.name = t[4]:match("%%60(.*)%%60")
        else
            _debug_log("couldn't parse this link: " .. str, debug)
            return {}
        end
    else
        search.name = str:match("%%60(.*)%%60")
    end

    if search.name == nil then
        _debug_log("couldn't parse this link: " .. str, debug)
        return {}
    end

    if search.name:sub(1, 1) == "~" then
        search.shortened = true
        search.name = search.name:sub(2, -1)
    end
    return search
end

local function report_broken_link(link, search_object, replacement)
    -- TODO: how to unescape html elements like [?
    return pandoc.Code(pandoc.utils.stringify(link.content))
end

function Link(link)
    -- do not process regular links ----
    if not link.target:match("%%60") then
        return link
    end

    -- lookup item ----
    local search = build_search_object(link.target)
    local item = lookup(search)

    -- determine replacement, used if no link text specified ----
    local original_text = pandoc.utils.stringify(link.content)
    local replacement = search.name
    if search.shortened then
        local t = mysplit(search.name, ".")
        replacement = t[#t]
    end

    -- set link text ----
    if original_text == "" and replacement ~= nil then
        link.content = pandoc.Code(replacement)
    end

    -- report broken links ----
    if item == nil then
        return report_broken_link(link, search)
    end
    link.target = item.uri:gsub("%$$", search.name)


    return link
end

function Code(code)
    if (not autolink) or contains(code.classes, autolink_ignore_token) then
        return code
    end

    -- allow text for lookup to be simple function call
    -- and also support shortened syntax (~~ prefix)
    -- e.g. my_func() -> my_func
    -- e.g. a.b.call() -> a.b.call
    -- e.g. ~~my_func() -> my_func
    local text

    -- detect and remove shortening syntax (~~ prefix)
    local is_shortened = code.text:sub(1, 2) == "~~"
    local is_short_dot = code.text:sub(1, 3) == "~~."
    local unprefixed = code.text:gsub("^~~%.?", "")
    if unprefixed:match("%(%s*%)") then
        text = unprefixed:gsub("%(%s*%)", "")
    else
        text = unprefixed
    end


    -- return code.attr
    local search = build_search_object("%60" .. text .. "%60")
    local item = lookup(search)

    -- determine replacement, used if no link text specified ----
    if item == nil then
        code.text = unprefixed
        return code
    end

    -- shorten text if shortening syntax used
    if is_shortened then
        -- keep text after last period (.)
        local split = mysplit(unprefixed, ".")
        if #split > 0 then
            local new_name = split[#split]
            if is_short_dot then
                -- if shortened with dot, keep the dot
                new_name = "." .. new_name
            end
            code.text = new_name
        else
            code.text = unprefixed
        end
    end


    return pandoc.Link(code, item.uri:gsub("%$$", search.name))
end

local function fixup_json(json, prefix, attach)
    table.insert(prefixes, prefix)
    for _, item in ipairs(json.items) do
        item.prefix_index = #prefixes
    end
    table.insert(inventory, json)
end

local function quote(value)
    if value == nil or value == false then
        return "false"
    elseif type(value) == "number" then
        return tostring(value)
    end
    return string.format("%q", value)
end

local function write_cache(cache_dir, cache_file)
    local out = { "return {P={" }
    for _, prefix in ipairs(prefixes) do
        out[#out + 1] = quote(prefix) .. ","
    end
    out[#out + 1] = "},I={"
    for name, rows in pairs(rows_by_name) do
        local parts = {}
        for i, value in ipairs(rows) do
            parts[i] = quote(value)
        end
        out[#out + 1] = "[" .. quote(name) .. "]={" .. table.concat(parts, ",") .. "},\n"
    end
    out[#out + 1] = "}}"
    local fn = load(table.concat(out))
    if fn == nil then
        return
    end

    -- write atomically (pages render concurrently), then drop stale caches
    pandoc.system.make_directory(cache_dir, true)
    local tmp_file = string.format("%s.%d.%d.tmp", cache_file, os.time(), math.random(1, 1000000000))
    local file = io.open(tmp_file, "wb")
    if file == nil then
        return
    end
    file:write(string.dump(fn, true))
    file:close()
    os.rename(tmp_file, cache_file)
    for _, name in ipairs(pandoc.system.list_directory(cache_dir)) do
        local path = cache_dir .. "/" .. name
        if name:match("%.luac$") and path ~= cache_file then
            os.remove(path)
        end
    end
end

-- sources: list of {base = path without extension, prefix = uri prefix}
local function load_inventories(sources, flat_aliases)
    -- read the sources (a .txt inventory wins over a .json one) and compute the cache key
    local key_parts = { "interlinks-cache-1", _VERSION }
    for _, src in ipairs(sources) do
        src.txt = read_file(src.base .. ".txt")
        if src.txt == nil then
            src.json = read_file(src.base .. ".json")
        end
        key_parts[#key_parts + 1] = src.base .. "\n" .. src.prefix .. "\n" .. (src.txt or src.json or "")
    end
    for _, name_pair in ipairs(flat_aliases) do
        key_parts[#key_parts + 1] = name_pair[1] .. "\n" .. alias_prefix(name_pair[2])
    end

    local cache_dir
    local cache_file
    if quarto.project.directory then
        cache_dir = quarto.project.directory .. "/.quarto/interlinks"
        cache_file = cache_dir .. "/" .. pandoc.utils.sha1(table.concat(key_parts, "\0")) .. ".luac"
        local bytes = read_file(cache_file, "rb")
        if bytes then
            local fn = load(bytes, "=interlinks-cache", "b")
            local ok, data = pcall(fn or error)
            if ok and type(data) == "table" then
                prefixes = data.P
                rows_by_name = data.I
                return
            end
        end
    end

    -- no (usable) cache, so parse the inventories
    for _, src in ipairs(sources) do
        local json
        if src.txt then
            json = parse_inv_text(src.txt)
        elseif src.json then
            json = decode_json(src.json)
        end
        if json ~= nil then
            fixup_json(json, src.prefix)
        end
    end
    prepend_aliases(flat_aliases)

    for _, inv in ipairs(inventory) do
        for _, item in ipairs(inv.items) do
            local rows = rows_by_name[item.name]
            if rows == nil then
                rows = {}
                rows_by_name[item.name] = rows
            end
            rows[#rows + 1] = item.domain or false
            rows[#rows + 1] = item.role or false
            rows[#rows + 1] = item.prefix_index
            rows[#rows + 1] = item.uri
        end
    end
    inventory = {}

    if cache_file then
        pcall(write_cache, cache_dir, cache_file)
    end
end

return {
    {
        Meta = function(meta)
            local json
            local prefix
            local aliases

            -- set globals from config
            if meta.interlinks and meta.interlinks.autolink then
                autolink = true
            else
                autolink = false
            end

            local aliases
            if meta.interlinks and meta.interlinks.aliases then
                aliases = meta.interlinks.aliases
            else
                aliases = {}
            end

            -- process sources (sorted, so the order and cache key are stable)
            local sources = {}
            if meta.interlinks and meta.interlinks.sources then
                for k, v in pairs(meta.interlinks.sources) do
                    sources[#sources + 1] = {
                        base = quarto.project.offset .. "/_inv/" .. k .. "_objects",
                        prefix = pandoc.utils.stringify(v.url),
                    }
                end
            end
            table.sort(sources, function(a, b) return a.base < b.base end)
            sources[#sources + 1] = { base = quarto.project.offset .. "/objects", prefix = "/" }

            local flat_aliases = flatten_alias_list(aliases)
            table.sort(flat_aliases, function(a, b)
                if a[1] ~= b[1] then
                    return a[1] < b[1]
                end
                return alias_prefix(a[2]) < alias_prefix(b[2])
            end)

            load_inventories(sources, flat_aliases)
        end
    },
    {
        Link = Link,
        Code = Code
    }
}
