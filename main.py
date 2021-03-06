import numpy as np
import pandas as pd

# Read in all data

data = pd.read_csv('201706-citibike-tripdata.csv').drop(['bikeid','usertype','birth year','gender'], axis=1)
data['starttime'] = pd.to_datetime(data['starttime'])
data['stoptime'] = pd.to_datetime(data['stoptime'])



# Clean up station information

station = np.vstack([data[['start station id','start station name',
                           'start station latitude','start station longitude']],
                     data[['end station id','end station name',
                           'end station latitude','end station longitude']]])

station = pd.DataFrame(station, columns=['station id','station name',
                                         'station latitude','station longitude'])

station = station.drop_duplicates().sort_values('station id')
station = station[station['station name'] != 'LPI Facility'].reset_index(drop=True)



# Calculate the stock of each station

C = pd.DataFrame([])

for key in station['station id']:
    temp = data[(data['start station id'] == key) | (data['end station id'] == key)].copy()
    temp['change'] = np.where(temp['start station id'] == key, -1, 1)
    temp['changetime'] = np.where(temp['start station id'] == key, temp['starttime'], temp['stoptime'])
    temp['changetime'] = temp['changetime'].dt.floor('15min') # Down sampling into 15 minutes

    change = temp.groupby('changetime')['change'].sum().reset_index() # Calculate the total change in 15 minutes
    change['time'] = change['changetime'].dt.time # Remove the date information

    stock = change.groupby('time')['change'].mean().cumsum() + 12 # Calculate the monthly average
    
    C[key] = stock

C = C.fillna(method='ffill')



# Set the filter
P = ((C < 5) | (C > 20)).astype('float')



import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.animation as animation
%matplotlib inline

from mpl_toolkits.basemap import Basemap

fig = plt.figure(figsize=(14,19.3))
ax = fig.add_subplot(111)



# Read in New York map
bmap = Basemap(projection='merc', lat_ts=40.65,
               llcrnrlat=40.65, urcrnrlat=40.84,
               llcrnrlon=-74.08, urcrnrlon=-73.90,
               resolution=None, ax=ax)

shp_info = bmap.readshapefile('new-york_new-york_osm_roads',
                              'shp', drawbounds=True, linewidth=0.1)



# Set the color threshold
norm = mpl.colors.Normalize(vmin=-50, vmax=70)
sm = mpl.cm.ScalarMappable(cmap='bwr_r', norm=norm) # Red for insufficient, blue for excess

color = sm.to_rgba(C.iloc[0,:])
color[:, -1] = P.iloc[0,:]

x, y = bmap(station['station longitude'].values, 
            station['station latitude'].values)
scat = bmap.scatter(x, y, s=50, facecolors=color, edgecolors='k', lw=0.05)
text = ax.text(500, 500, None, size=20)

fig.tight_layout(pad=1.03)



# Set Animation

def update(i):
    color = sm.to_rgba(C.iloc[i,:])
    color[:, -1] = P.iloc[i,:]
    
    scat.set_facecolors(color)
    text.set_text(C.index[i])

anim = animation.FuncAnimation(fig, update, frames=C.shape[0], interval=200)
anim.save('flow.mp4')



# Focus on specific station

loc = int(station[station['station name'] == 'E 47 St & Park Ave']['station id'])

temp = data[(data['start station id'] == loc) | (data['end station id'] == loc)].copy()
temp['change'] = np.where(temp['start station id'] == loc, -1, 1)
temp['type'] = temp['change'] > 0

temp['changetime'] = np.where(temp['start station id'] == loc, temp['starttime'], temp['stoptime'])
temp['changetime'] = temp['changetime'].dt.floor('15min') # Down sampling into 15 minutes



# Calculate return, borrow and stock

b = temp[temp['type'] == 0].groupby(['changetime'])['change'].sum().reset_index() 
b['time'] = b['changetime'].dt.hour 
b = b.groupby('time')['change'].mean() 

r = temp[temp['type'] == 1].groupby(['changetime'])['change'].sum().reset_index() 
r['time'] = r['changetime'].dt.hour 
r = r.groupby('time')['change'].mean()

s = temp.groupby('changetime')['change'].sum().reset_index() 
s['time'] = s['changetime'].dt.hour 
s = s.groupby('time')['change'].mean().cumsum() + 12 



# Draw the graph

plt.style.use('seaborn')
plt.figure(figsize = (12, 6))

plt.plot(s, 'k--', label = 'stock')
plt.bar(left = r.index - 0.2, height = r.values, width = 0.4, facecolor ='blue', label = 'return')
plt.bar(left = b.index + 0.2, height = -b.values, width = 0.4, facecolor ='red', label = 'borrow')

plt.xlim([-1,24])
plt.xlabel('Hour')
plt.ylabel('Count')

plt.legend()
plt.tight_layout(pad=1.03)

plt.savefig('E_47_St_&_Park_Ave.png', dpi=300, facecolor='w')
