[X]1. generate arbitrary data
[ ]2. calibrate on arbitrary data to discover most acurate loss funciton
[ ]3. Use accurate loss function to overfit to exclude algorithms 
[ ]4. Use best few algorithms and loss function going forward
[ ]5. Single workflow generalization experiments 
	[ ]5.1 Diversity of CPU:Data Ratio needed?
	[ ]5.2 Budget required for ground truth data
		5.2.1 Strips?
		5.2.2 Squares?
		5.2.3 Something else?

        W5      E   E    E    E

        W4                    E
        
        W3   X  X             E 

        W2   X  X             E  

        W1   X  X                         

            1N  2N  4N  6N  8N

        error
        ground-truth data obtaining time
    
[ ]6. Accross Workflow (train on N workflows, Test on ALL workflows)
	[ ]6.1 Chain Only
	[ ]6.2 Forkjoin Only
	[ ]6.3 Forkjoin AND chain only
	[ ]6.4 Duno, some subset of workflows??? (Easiest to install?)(same research area?)

[ ]7. Simulator sophistication required (single workflows at a time using previous results to inform)


