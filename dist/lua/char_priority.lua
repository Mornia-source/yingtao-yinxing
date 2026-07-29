-- 樱桃音形专用过滤器：候选队列前段重排，优先级从高到低：
--   1. 全码精确匹配的候选（当前已经打的编码正好是它自己的编码，不用再
--      多打字就能选中）——按 quality 排，不受字数限制。
--   2. 其余候选（还需要多打字才能补全，比如4码全码打完时冒出来的
--      6码精确码提示）——先按字数少的优先，同字数内再按 quality 排。
-- "精确匹配"用 cand.comment 是否为空来判断：table_translator 只在
-- 候选需要补全时才会给 comment 挂上剩余编码提示，精确匹配的候选
-- comment 天生是空的，不用额外传参数、也不用去猜当前输入长度。
--
-- 起因：Rime 的补全(completion)候选是按编码本身在字根树里的顺序枚举
-- 出来的，不是全局按词频/权重排序的；tier_boost.py 已经把"编码位数越少
-- 权重越高"这条规则揉进了词典权重(2位单字 > 3位简码 > 4位全码，同位数
-- 内再按词频)，配合这里的重排，"字优先于词""位数少的优先""同位数内
-- 更常用的优先""全码精确匹配的例外"这几条规则就都能满足。
--
-- 之前直接用 table.sort(cands, function(a,b) return a.quality>b.quality end)
-- 上过一次线，结果把候选顺序搞得更乱——推测是候选里混入了quality不是
-- 普通数字的情况(比如标点/翻译类候选)，导致比较函数行为不一致、
-- table.sort 中途出错但还是产生了部分交换。这里先把每个候选的quality
-- 取到一个纯数字数组里校验过，校验不过就直接放弃排序、原样透传，
-- 保证任何情况下都不会比"完全不排序"更差。
--
-- 方案patch中引用方式：
--  engine/filters/+:
--  - lua_filter@*char_priority*Char_priority_filter

local WINDOW = 20

local function sorted_or_original(buf)
    local n = #buf
    if n <= 1 then return buf end

    local quality = {}
    local length = {}
    local exact = {}
    for i = 1, n do
        local q = buf[i].quality
        if type(q) ~= "number" then
            return buf -- 取不到有效权重，原样透传，不冒险排序
        end
        quality[i] = q
        length[i] = utf8.len(buf[i].text) or 99
        local c = buf[i].comment
        exact[i] = (c == nil or c == "")
    end

    local idx = {}
    for i = 1, n do idx[i] = i end

    local ok = pcall(table.sort, idx, function(a, b)
        -- 第一优先级：全码精确匹配的候选整体排在需要继续补全的候选前面。
        if exact[a] ~= exact[b] then
            return exact[a]
        end
        if exact[a] then
            -- 都是精确匹配：不受字数限制，直接按权重比，让"全码精确
            -- 匹配"真正例外于"字数少优先"这条规则。
            if quality[a] ~= quality[b] then
                return quality[a] > quality[b]
            end
            return a < b
        end
        -- 都是补全候选：字数少的排前面，同字数内再按权重排。
        if length[a] ~= length[b] then
            return length[a] < length[b]
        end
        if quality[a] ~= quality[b] then
            return quality[a] > quality[b]
        end
        return a < b -- 权重也相同时保持原有先后顺序，做稳定排序
    end)
    if not ok then
        return buf
    end

    local result = {}
    for i = 1, n do
        result[i] = buf[idx[i]]
    end
    return result
end

local function Char_priority_filter(input)
    local buf = {}
    local count = 0
    for cand in input:iter() do
        count = count + 1
        if count <= WINDOW then
            table.insert(buf, cand)
        else
            if #buf > 0 then
                for _, c in ipairs(sorted_or_original(buf)) do
                    yield(c)
                end
                buf = {}
            end
            yield(cand)
        end
    end
    for _, c in ipairs(sorted_or_original(buf)) do
        yield(c)
    end
end

return {Char_priority_filter = Char_priority_filter}
