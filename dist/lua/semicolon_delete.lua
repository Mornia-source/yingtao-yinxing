-- 樱桃音形专用处理器：分号(;)的两段式功能。
--   闲置状态(没有正在composing)下先按一次 ; ：吞掉、不上屏，等下一个键。
--     - 下一个键是 i：撤回上一次上屏的内容(不管上一次上屏了几个字)，
--       用 commit_notifier 记录上次提交文本的长度，靠连续按退格实现。
--     - 下一个键还是 ; ，或者是回车：把等待中的分号真正提交(字面";")。
--     - 其它任意键：先把等待中的分号提交，再放行当前键正常处理。
--   打字过程中(正在composing)完全不介入，分号该怎样就怎样。
--
-- 方案patch中引用方式：
--  engine/processors 里 punctuator 之前插入：
--  - lua_processor@*semicolon_delete*Semicolon_delete

local kRejected = 0
local kAccepted = 1
local kNoop = 2

local KEY_SEMICOLON = 0x3b
local KEY_I = 0x69
local KEY_RETURN = 0xff0d
local KEY_KP_ENTER = 0xff8d

local function init(env)
    env.yt_pending_semi = false
    env.yt_last_commit_len = 0
    pcall(function()
        env.yt_commit_notifier = env.engine.context.commit_notifier:connect(function(ctx)
            local text = ctx:get_commit_text()
            if text and text ~= "" then
                local n = utf8.len(text)
                if n then
                    env.yt_last_commit_len = n
                end
            end
        end)
    end)
end

local function fini(env)
    if env.yt_commit_notifier then
        pcall(function() env.yt_commit_notifier:disconnect() end)
    end
end

local function commit_semicolon(env)
    pcall(function() env.engine:commit_text(";") end)
end

local function do_backspace(env, n)
    pcall(function()
        for _ = 1, n do
            env.engine:process_key(KeyEvent("BackSpace"))
        end
    end)
end

local function Semicolon_delete(key, env)
    if key:release() then
        return kNoop
    end

    local context = env.engine.context
    local ok, ascii_mode = pcall(function() return context:get_option("ascii_mode") end)
    if ok and ascii_mode then
        return kNoop -- 西文模式下完全不介入
    end
    if context:is_composing() then
        -- 正在打字时不介入，分号照常走后面的处理器(比如当标点)。
        env.yt_pending_semi = false
        return kNoop
    end

    local code = key.keycode

    if env.yt_pending_semi then
        env.yt_pending_semi = false
        if code == KEY_I then
            local n = env.yt_last_commit_len or 0
            if n > 0 then
                do_backspace(env, n)
                env.yt_last_commit_len = 0
            end
            return kAccepted
        elseif code == KEY_SEMICOLON or code == KEY_RETURN or code == KEY_KP_ENTER then
            commit_semicolon(env)
            return kAccepted
        else
            -- 其它键：先把分号原样打出来，再放行这个键正常处理。
            commit_semicolon(env)
            return kNoop
        end
    end

    if code == KEY_SEMICOLON then
        env.yt_pending_semi = true
        return kAccepted -- 先吞掉，等下一个键决定做什么
    end

    return kNoop
end

return { init = init, func = Semicolon_delete, fini = fini }
