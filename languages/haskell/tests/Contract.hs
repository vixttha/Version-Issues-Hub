draw :: Int -> [a] -> ([a], [a])
draw capacity cards = splitAt capacity cards

main :: IO ()
main =
  if draw 2 ([1, 2, 3] :: [Int]) == ([1, 2], [3])
     && draw 2 ([] :: [Int]) == ([], [])
  then pure ()
  else fail "Ordered draw contract mismatch"
