local key_pattern = ARGV[1]
local min = ARGV[2]

local cursor = 0
local deleted_streams = 0

repeat
    local result = redis.call('SCAN', cursor, 'MATCH', key_pattern)
    for _,key in ipairs(result[2]) do
        if next(redis.call('XRANGE', key, min, "+", 'COUNT', 1)) == nil then
            redis.call('DEL', key)
            deleted_streams = deleted_streams + 1
        end
    end
    cursor = tonumber(result[1])
until cursor == 0

return deleted_streams
