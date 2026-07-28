-- 樱桃音形专用过滤器：候选队列前段按权重(quality)从高到低重排。
--
-- 起因：Rime 的补全(completion)候选是按编码本身在字根树里的顺序枚举
-- 出来的，不是全局按词频/权重排序的；tier_boost.py 已经把"编码位数越少
-- 权重越高"这条规则揉进了词典权重(2位单字 > 3位简码 > 4位全码，同位数
-- 内再按词频)，只要把候选按quality重新排一遍，"字优先于词""位数少的
-- 优先""同位数内更常用的优先"这几条规则就都自然满足了，不需要再单独
-- 判断文本是不是单字、是不是精确匹配。
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
    for i = 1, n do
        local q = buf[i].quality
        if type(q) ~= "number" then
            return buf -- 取不到有效权重，原样透传，不冒险排序
        end
        quality[i] = q
    end

    local idx = {}
    for i = 1, n do idx[i] = i end

    local ok = pcall(table.sort, idx, function(a, b)
        if quality[a] ~= quality[b] then
            return quality[a] > quality[b]
        end
        return a < b -- 权重相同时保持原有先后顺序，做稳定排序
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
