local function clamp(value, lower, upper)
  return math.max(lower, math.min(value, upper))
end

local function move(x, y, dx, dy)
  return clamp(x + dx, 0, 9), clamp(y + dy, 0, 4)
end

local x, y = move(8, 1, 3, -2)
assert(x == 9 and y == 0, "movement hit the wrong axis bounds")
