from single_workflow_heatmap import *

data={
	'single_workflow':{
		60:"../../../koa-rsync/workflow/single-workflow-fast/pickles60/*-koa.pickled",
		300:"../../../koa-rsync/workflow/single-workflow-fast/pickles300/*-koa.pickled",
		600:"../../../koa-rsync/workflow/single-workflow-fast/pickles600/*-koa.pickled",
		1800:"../../../koa-rsync/workflow/single-workflow-fast/pickles1800/*-koa.pickled",
		3600:"../../../koa-rsync/workflow/single-workflow-fast/pickles3600/*-koa.pickled",
		7200:"../../../koa-rsync/workflow/single-workflow-fast/pickles7200/*-koa.pickled",
		18000:"../../../koa-rsync/workflow/single-workflow-fast/pickles18000/*-koa.pickled",
		86400:"../../../koa-rsync/workflow/single-workflow/pickles/*-koa.pickled"
	},	
	'single_sample':{
		60:"../../../koa-rsync/workflow/single-sample-fast/pickles60/*-koa.pickled",
		300:"../../../koa-rsync/workflow/single-sample-fast/pickles300/*-koa.pickled",
		600:"../../../koa-rsync/workflow/single-sample-fast/pickles600/*-koa.pickled",
		1800:"../../../koa-rsync/workflow/single-sample-fast/pickles1800/*-koa.pickled",
		3600:"../../../koa-rsync/workflow/single-sample-fast/pickles3600/*-koa.pickled",
		7200:"../../../koa-rsync/workflow/single-sample-fast/pickles7200/*-koa.pickled",
		18000:"../../../koa-rsync/workflow/single-sample-fast/pickles18000/*-koa.pickled",
		86400:"../../../koa-rsync/workflow/single-sample/pickles/*-koa.pickled"
	}
}

data47={
	'single_workflow':{
		60:"../../../koa-rsync/workflow/single-workflow-fast/pickles60/*47-koa.pickled",
		300:"../../../koa-rsync/workflow/single-workflow-fast/pickles300/*47-koa.pickled",
		600:"../../../koa-rsync/workflow/single-workflow-fast/pickles600/*47-koa.pickled",
		1800:"../../../koa-rsync/workflow/single-workflow-fast/pickles1800/*47-koa.pickled",
		3600:"../../../koa-rsync/workflow/single-workflow-fast/pickles3600/*47-koa.pickled",
		7200:"../../../koa-rsync/workflow/single-workflow-fast/pickles7200/*47-koa.pickled",
		18000:"../../../koa-rsync/workflow/single-workflow-fast/pickles18000/*47-koa.pickled",
		86400:"../../../koa-rsync/workflow/single-workflow/pickles/*47-koa.pickled"
	},	
	'single_sample':{
		60:"../../../koa-rsync/workflow/single-sample-fast/pickles60/*47-koa.pickled",
		300:"../../../koa-rsync/workflow/single-sample-fast/pickles300/*47-koa.pickled",
		600:"../../../koa-rsync/workflow/single-sample-fast/pickles600/*47-koa.pickled",
		1800:"../../../koa-rsync/workflow/single-sample-fast/pickles1800/*47-koa.pickled",
		3600:"../../../koa-rsync/workflow/single-sample-fast/pickles3600/*47-koa.pickled",
		7200:"../../../koa-rsync/workflow/single-sample-fast/pickles7200/*47-koa.pickled",
		18000:"../../../koa-rsync/workflow/single-sample-fast/pickles18000/*47-koa.pickled",
		86400:"../../../koa-rsync/workflow/single-sample/pickles/*47-koa.pickled"
	}
}
for key in data:
	each=data[key]
	pickle_files=glob(each)
	datat=load_and_group_pickles(pickle_files)
	dv={}
	for group in datat.values():
			a,b=process_experiment_group(group)
			dv[a]=b
	data[key]=dv
	
for key in data47:
	each=data47[key]
	pickle_files=glob(each)
	datat=load_and_group_pickles(pickle_files)
	dv={}
	for group in datat.values():
			a,b=process_experiment_group(group)
			dv[a]=b
	data47[key]=dv