require "json"

def valid_title?(json)
  title = JSON.parse(json)["title"]
  title.is_a?(String) && !title.strip.empty?
end

raise "valid title rejected" unless valid_title?('{"title":"Guide"}')
raise "blank title accepted" if valid_title?('{"title":" "}')
raise "missing title accepted" if valid_title?('{}')
