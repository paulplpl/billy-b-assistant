try:
    from .music_visualizer import BillyBassVisualizer, VisualizerConfig
    from .logger import logger
except: #For standalone debugging
    from music_visualizer import BillyBassVisualizer, VisualizerConfig
    import logging 
    logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        #logging.FileHandler('app.log')  # File output
    ]
)
    logger = logging.getLogger(__name__)
    import traceback
    import sys
    
viz = BillyBassVisualizer(
    cfg=VisualizerConfig(blocksize=1024, debug=True,bass_gain=5500.0,voice_gain=5500.0),
    arecord_device="loop_capture",
)
def start_viz():
    
    logger.info("Starting sync flapper", "🔌")
    viz.start()

def stop_viz():
    logger.info("Stopping sync flapper", "🔌")
    viz.stop()

# for debug
if __name__ == "__main__":
    try:
        start_viz()
    except Exception as e:
        logger.error("❌ Unhandled exception occurred:", e)
        traceback.print_exc()
        stop_viz()
        sys.exit(1)