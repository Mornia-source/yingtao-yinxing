-- 樱桃音形专用过滤器：把候选队列前段里的单字候选提到多字候选前面。
-- 起因：Rime 的补全(completion)候选是按编码串本身在字根树里的顺序
-- 枚举出来的，并不是全局按词频重新排序；纯粹靠权重加成没法让"位数少
-- 的候选(单字)排到位数多的候选(词/句)前面"。这里只对候选流最前面的
-- 一小段做"单字优先、内部顺序不变"的稳定重排，之后的候选原样透传，
-- 不会影响后面正常的补全展示、也不会有明显延迟。

local WINDOW = 20

local function filter(input, env)
    return coroutine.wrap(function()
        local singles = {}
        local multis = {}
        local count = 0
        for cand in input:iter() do
            count = count + 1
            if count <= WINDOW then
                if utf8.len(cand.text) == 1 then
                    table.insert(singles, cand)
                else
                    table.insert(multis, cand)
                end
            else
                if #singles > 0 or #multis > 0 then
                    for _, c in ipairs(singles) do
                        coroutine.yield(c)
                    end
                    for _, c in ipairs(multis) do
                        coroutine.yield(c)
                    end
                    singles = {}
                    multis = {}
                end
                coroutine.yield(cand)
            end
        end
        for _, c in ipairs(singles) do
            coroutine.yield(c)
        end
        for _, c in ipairs(multis) do
            coroutine.yield(c)
        end
    end)
end

return filter
