"""Main CLI entry point."""
import os
import sys
import argparse
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Add src to path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
from infrastructure.verifiers.fever_groundtruth_verifier import FEVERGroundTruthVerifier
from infrastructure.verifiers.llm_evidence_evaluator import LLMEvidenceEvaluator
from infrastructure.storage.jsonl_storage import JSONLStorage
from infrastructure.llm.openai_client import OpenAIClient
from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
from application.use_cases.run_episode import RunEpisode
from application.use_cases.run_experiment import RunExperiment


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run MAS Cheap Talk experiments")
    parser.add_argument(
        "--config",
        type=str,
        default="src/interfaces/configs/milestone1.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        help="Override number of tasks from config"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Override output path from config"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    print(f"Loading configuration from: {args.config}")
    config = load_config(args.config)
    
    # Override config with CLI args if provided
    if args.num_tasks:
        config['experiment']['num_tasks'] = args.num_tasks
    if args.output:
        config['output']['path'] = args.output
    
    print(f"\nExperiment: {config['experiment']['name']}")
    print(f"Tasks: {config['experiment']['num_tasks']}")
    print(f"Protocol: {config['protocol']['name']}")
    print(f"Deviations: {config['deviations']}")
    
    # Get API key
    api_key = None
    if config['llm']['provider'] == 'openai':
        api_key_env = config['llm'].get('api_key_env', 'OPENAI_API_KEY')
        api_key = os.getenv(api_key_env)
        if not api_key:
            print(f"\nError: {api_key_env} environment variable not set")
            print("Please set it in .env file or export it:")
            print(f"  export {api_key_env}=your-api-key")
            sys.exit(1)
    
    # Initialize components with dependency injection
    print("\nInitializing components...")
    
    # Dataset repository
    dataset_repo = HFFEVERRepository(
        split=config['dataset']['split'],
        num_samples=config['dataset']['num_samples'],
        seed=config['experiment']['seed']
    )
    
    # Verifier (optional: LLM-based evidence scoring per sentence, then aggregate)
    verifier_cfg = config.get('verifier', {})
    llm_evaluator = None
    evidence_weights = None
    if verifier_cfg.get('use_llm_evidence_eval', False):
        eval_client = OpenAIClient(
            model=config['llm']['model'],
            api_key=api_key
        )
        llm_evaluator = LLMEvidenceEvaluator(llm_client=eval_client, temperature=0.0, max_tokens=800)
        evidence_weights = verifier_cfg.get('evidence_score_weights', {"string_match": 0.5, "llm": 0.5})
    verifier = FEVERGroundTruthVerifier(
        use_semantic_matching=verifier_cfg.get('use_semantic_matching', False),
        llm_evidence_evaluator=llm_evaluator,
        evidence_score_weights=evidence_weights,
    )
    
    # Storage
    storage = JSONLStorage(filepath=config['output']['path'])
    
    # Protocol
    if config['protocol']['name'] == 'p1_evidence_first':
        protocol = P1EvidenceFirstProtocol()
    else:
        raise ValueError(f"Unknown protocol: {config['protocol']['name']}")
    
    # Run episode use case
    run_episode = RunEpisode(
        protocol=protocol,
        verifier=verifier,
        model_name=config['llm']['model'],
        api_key=api_key,
        lambda_cost=config['payoff']['lambda_cost'],
        mu_penalty=config['payoff']['mu_penalty']
    )
    
    # Run experiment use case
    run_experiment = RunExperiment(
        run_episode=run_episode,
        dataset_repo=dataset_repo,
        storage=storage,
        num_tasks=config['experiment']['num_tasks'],
        deviation_types=config['deviations']
    )
    
    print("\nStarting experiment...")
    print("="*60)
    
    try:
        # Execute experiment
        results = run_experiment.execute_sync()
        
        # Save summary
        summary_path = config['output'].get('summary_path', 'results/summary.json')
        run_experiment.save_summary(results, summary_path)
        
        print("\nExperiment completed successfully!")
        print(f"Results saved to: {config['output']['path']}")
        print(f"Summary saved to: {summary_path}")
        
    except Exception as e:
        print(f"\nError during experiment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
