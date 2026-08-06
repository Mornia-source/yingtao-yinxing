-- 樱桃音形专用过滤器：emoji 支持。
--   候选里如果有某个词条的文本正好是已知的 emoji 名字（比如"疲惫"
--   "微笑"），就在紧挨着候选1的位置(候选2)插入对应的 emoji；如果
--   同一批候选里匹配上了不止一个名字/一个名字对应多个 emoji，
--   就依次排在候选3、4、5...后面，候选1本身不受影响。
--
--   emoji 候选是过滤器现造出来的合成候选，不是词典里真实存在、能被
--   user_dict 记录使用频率的词条，所以天然不会因为选用过 emoji 就
--   提高它以后的优先级——每次都是同样的位置、同样的顺序。
--
--   数据来源：build/gen_emoji.py 处理 iDvel/rime-ice 的
--   opencc/emoji.txt 生成 lua/yingtao_emoji.txt（名字\tab
--   emoji1 emoji2...），这里在模块加载时读一次、缓存成 Lua table。
--   （这个过滤器用 *文件名*函数名 的方式引用，不支持 init(env)/env
--   参数那一套，只能用模块级别的 local 变量自己管生命周期——模块
--   本身只会被 require 一次，效果跟 init 一次是一样的。）
--
-- 方案patch中引用方式：
--  engine/filters/+:（放在 char_priority 之后，因为要在字数/权重
--  排序定下来以后再插入 emoji，不然会被后面的排序打乱位置）
--  - lua_filter@*yingtao_emoji*Yingtao_emoji_filter

local WINDOW = 30

local function load_emoji_table()
    local table_ = {}
    local ok = pcall(function()
        local path = rime_api.get_user_data_dir() .. "/lua/yingtao_emoji.txt"
        local f = io.open(path, "r")
        if not f then return end
        for line in f:lines() do
            local name, emojis = line:match("^(.-)\t(.+)$")
            if name and emojis then
                local list = {}
                for e in emojis:gmatch("%S+") do
                    table.insert(list, e)
                end
                if #list > 0 then
                    table_[name] = list
                end
            end
        end
        f:close()
    end)
    if not ok then
        return {}
    end
    return table_
end

local EMOJI_TABLE = load_emoji_table()

local function insert_emoji(buf)
    local n = #buf
    if n == 0 then
        return buf
    end
    local seen = {}
    local emoji_cands = {}
    for i = 1, n do
        local list = EMOJI_TABLE[buf[i].text]
        if list then
            for _, e in ipairs(list) do
                if not seen[e] then
                    seen[e] = true
                    local ok, ec = pcall(function()
                        return Candidate("emoji", buf[1].start, buf[1]._end, e, "")
                    end)
                    if ok and ec then
                        table.insert(emoji_cands, ec)
                    end
                end
            end
        end
    end
    if #emoji_cands == 0 then
        return buf
    end
    local result = { buf[1] }
    for _, ec in ipairs(emoji_cands) do
        table.insert(result, ec)
    end
    for i = 2, n do
        table.insert(result, buf[i])
    end
    return result
end

local function Yingtao_emoji_filter(input)
    local buf = {}
    local count = 0
    for cand in input:iter() do
        count = count + 1
        if count <= WINDOW then
            table.insert(buf, cand)
        else
            if #buf > 0 then
                for _, c in ipairs(insert_emoji(buf)) do
                    yield(c)
                end
                buf = {}
            end
            yield(cand)
        end
    end
    for _, c in ipairs(insert_emoji(buf)) do
        yield(c)
    end
end

return { Yingtao_emoji_filter = Yingtao_emoji_filter }
