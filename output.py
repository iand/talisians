import pickle
from scanner import Link

if __name__ == "__main__":
  f = open("links.pkl", "rb")
  links = pickle.load(f)
  f.close()
  
  #~ links.sort(key=lambda x: x.frequency)
  links.sort(key=lambda x: x.score)
  
  print
  print
  
  for link in links:
    print link
    print link.get_sources_text(html=True)
    print
  
  print
