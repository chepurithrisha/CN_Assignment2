import pandas as pd
import matplotlib.pyplot as plt

df=pd.read_csv("d_results_h1.csv")

df10=df.head(10)


df10["servers_visited"]=df10["dns_ip"].apply(
    lambda x: len(x.split(";")) if isinstance(x,str) else 1
)

latencies=df10["round_trip_ms"]
lat_min=latencies.min()
lat_max=latencies.max()
lat_margin=(lat_max-lat_min)*0.2 if lat_max!=lat_min else 100

servers=df10["servers_visited"]
srv_min=servers.min()
srv_max=servers.max()
srv_margin=(srv_max-srv_min)*0.5 if srv_max!=srv_min else 0.5


fig,ax=plt.subplots(2,1,figsize=(10,8))


ax[0].bar(df10["hostname"],latencies,color="skyblue",edgecolor="black")
ax[0].set_title("DNS Query Latency for First 10 URLs (Host H1)")
ax[0].set_ylabel("Latency (ms)")
ax[0].set_ylim(lat_min-lat_margin,lat_max+lat_margin)
ax[0].tick_params(axis="x",rotation=45)


ax[1].bar(df10["hostname"],servers,color="orange",edgecolor="black")
ax[1].set_title("Number of DNS Servers Visited per Query")
ax[1].set_ylabel("Servers Visited")
ax[1].set_ylim(srv_min-srv_margin,srv_max+srv_margin)
ax[1].tick_params(axis="x",rotation=45)

plt.tight_layout()
plt.show()
