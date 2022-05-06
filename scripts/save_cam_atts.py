#%%
from simple_pyspin import Camera
from IPython import embed
with Camera() as cam:
    attributes = cam.camera_attributes.keys()

    with open('/home/clandinin/src/jackfish/misc/blackfly_atts.txt','a') as f:
        for attribute in attributes:
            f.write(attribute)
            f.write('\n')
# %%
