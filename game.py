from functools import lru_cache
import io
import sys
import numpy as np
import scipy
from thoughtcloud import ThoughtCloud, ImageColorGenerator
import matplotlib.pyplot as plt
from ipywidgets import widgets
import cairosvg
from PIL import ImageFilter, Image
from sklearn.preprocessing import normalize
import cProfile
import profile
import json
import pygame
from pygame.locals import *

window_size = 1000

with open("spaces/embedded_01.json") as f:
  concepts = json.load(f)

def rgb(hex):
  return np.array(tuple(int(hex[i:i+2], 16) for i in (0, 2, 4)))
colors = {
  "48cae4": (25.001,25.001),
  "ffb703": (75.001,25.001),
  "06d6a0": (25.001,75.001),
  "d00000": (75.001, 75.001)
}

def color_words(word, *args, **kwargs):
  color = dot_color_interpolation(concepts[word])
  return np_color_to_tuple(color)

def np_color_to_tuple(c):
  return tuple(int(i) for i in c)

def dot_color_interpolation(dot):
  c = np.array(list(colors.values()))
  p = np.array([dot])
  if int(dot[0]) == 40 and int(dot[1]) == 10:
    print(dot)
  dist = np.reciprocal(scipy.spatial.distance.cdist(p,c)).clip(0, np.finfo(dtype=np.float64).max)
  dist = normalize(dist ** 1/2,)
  ncol = np.array(list([rgb(i) for i in colors.keys()]))
  return np.matmul(dist,ncol)[0].clip(0,255)

def get_bg_color(w,h):
  wc =np_color_to_tuple(dot_color_interpolation((w,h)))
  return (255-wc[0],255-wc[1],255-wc[2])
from functools import lru_cache

def get_cloud(
    dot,
    wc_config={
      "background_color":None,
      "mode":"RGBA",
      "max_font_size":90,
      "random_state":0,
      "color_func":color_words,
    },
    mask_path="circle_small.png",
    fg_max_words=15,
    bg_max_words=7,
    fg_config={
      "scale": 4 * (window_size/500),
    },
    bg_config={
      "height": 60,
      "width": 60,
      "scale": 8 * (window_size/500),
      "min_font_size": 2,
      "font_step": 8
    }
  ):
  mask = np.array(Image.open(mask_path))
  wordcloud = ThoughtCloud(mask=mask, **fg_config,  **wc_config)
  wordcloud_bg = ThoughtCloud(**bg_config, **wc_config)
  c = np.array(list(concepts.values()))
  p = np.array([dot])
  dist = np.reciprocal(scipy.spatial.distance.cdist(p,c))
  d=sorted(list(zip(concepts.keys(), np.nan_to_num(dist[0]))), key=lambda x: x[1], reverse=True)
  return (
    wordcloud.generate_from_frequencies(frequencies=dict(d[:fg_max_words])),
    wordcloud_bg.generate_from_frequencies(frequencies=dict(d[:bg_max_words]))
  )

# @lru_cache(1000)
def get_cloud_images(w, h):
  wc_fg, wc_bg = get_cloud((w,h)) 
  # plot_concepts_with_dot(concepts, (w,h))
  return (wc_fg.to_image(), wc_bg.to_image())


margin = 0.1
def get_frame(w,h):
  im, im_bg = get_cloud_images(int(w/margin)*margin,int(h/margin)*margin) 
  color = get_bg_color(w,h)
  bg = Image.new('RGBA', im.size, color=color)
  bg.paste(im, (0,0),im)
  bg.paste(im_bg, (0,0),im_bg)
  blurred = bg.filter(ImageFilter.BoxBlur(10)) # Faster than gaussian, and the box look fits
  blurred.paste(im, (0,0),im)
  return blurred, color

pygame.init()

#Game loop begins
DISPLAYSURF = pygame.display.set_mode((window_size,window_size))
FPS = pygame.time.Clock()
while True:
  for event in pygame.event.get():              
    if event.type == QUIT:
        pygame.quit()
        sys.exit()
  # Take image as input 
  x,y = pygame.mouse.get_pos()
  image, color= get_frame(x/window_size*100,y/window_size*100)
    
  # Calculate mode, size and data 
  mode = image.mode 
  size = image.size 
  data = image.tobytes() 
    
  # Convert PIL image to pygame surface image 
  py_image = pygame.image.fromstring(data, size, mode) 
    
  # Construct rectangle around the image 
  rect = py_image.get_rect() 
  rect.center = window_size//2, window_size//2 
  DISPLAYSURF.fill(color)
  DISPLAYSURF.blit(py_image, rect)
  pygame.display.update()
  FPS.tick(30)