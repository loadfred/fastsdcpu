from PIL import Image
from typing import Any

from constants import DEVICE
from paths import FastStableDiffusionPaths
from backend.upscale.upscaler import upscale_image
from backend.models.lcmdiffusion_setting import DiffusionTask
from backend.upscale.tiled_upscale import generate_upscaled_image
from frontend.webui.image_variations_ui import generate_image_variations

_batch_count = 1


def user_value(
    value_type: type,
    message: str,
    default_value: Any,
) -> Any:
    try:
        value = value_type(input(message))
    except:
        value = default_value
    return value


def interactive_mode(
    config,
    context,
):
    print("=============================================")
    print("Welcome to FastSD CPU Interactive CLI")
    print("=============================================")
    print("> 1. Text to Image")
    print("> 2. Image to Image")
    print("> 3. Image Variations")
    print("> 4. EDSR Upscale")
    print("> 5. SD Upscale")
    option = user_value(
        int,
        "Enter a Diffusion Task number (1): ",
        1,
    )
    if option not in range(1, 6):
        print("Wrong Diffusion Task number!")
        exit()

    edit_settings = input("Edit default generation settings? (y/N): ")
    if edit_settings.upper() == "Y":
        interactive_settings(
            config,
            context,
        )

    if option == 1:
        interactive_txt2img(
            config,
            context,
        )
    elif option == 2:
        interactive_img2img(
            config,
            context,
        )
    elif option == 3:
        interactive_variations(
            config,
            context,
        )
    elif option == 4:
        interactive_edsr(
            config,
            context,
        )
    elif option == 5:
        interactive_sdupscale(
            config,
            context,
        )


def interactive_settings(
    config,
    context,
):
    global _batch_count
    settings = config.lcm_diffusion_setting
    print("Enter generation settings (leave empty to use current value)")
    print("> 1. Use LCM")
    print("> 2. Use LCM-Lora")
    print("> 3. Use OpenVINO")
    option = user_value(
        int,
        "Select inference model option (1): ",
        1,
    )
    if option not in range(1, 4):
        print("Wrong inference model option!")
        exit()

    settings.use_lcm_lora = False
    settings.use_openvino = False
    if option == 1:
        lcm_model_id = input(f"Enter LCM model ID ({settings.lcm_model_id}): ")
        if lcm_model_id != "":
            settings.lcm_model_id = lcm_model_id
    elif option == 2:
        settings.use_lcm_lora = True
        lcm_lora_id = input(
            f"Enter LCM-Lora model ID ({settings.lcm_lora.lcm_lora_id}): "
        )
        if lcm_lora_id != "":
            settings.lcm_lora.lcm_lora_id = lcm_lora_id
        base_model_id = input(
            f"Enter Base model ID ({settings.lcm_lora.base_model_id}): "
        )
        if base_model_id != "":
            settings.lcm_lora.base_model_id = base_model_id
    elif option == 3:
        settings.use_openvino = True
        openvino_lcm_model_id = input(
            f"Enter OpenVINO model ID ({settings.openvino_lcm_model_id}): "
        )
        if openvino_lcm_model_id != "":
            settings.openvino_lcm_model_id = openvino_lcm_model_id

    settings.use_offline_model = True
    settings.use_tiny_auto_encoder = True
    option = input("Work offline? (Y/n): ")
    if option.upper() == "N":
        settings.use_offline_model = False
    option = input("Use Tiny Auto Encoder? (Y/n): ")
    if option.upper() == "N":
        settings.use_tiny_auto_encoder = False

    settings.image_width = user_value(
        int,
        f"Image width ({settings.image_width}): ",
        settings.image_width,
    )
    settings.image_height = user_value(
        int,
        f"Image height ({settings.image_height}): ",
        settings.image_height,
    )
    settings.inference_steps = user_value(
        int,
        f"Inference steps ({settings.inference_steps}): ",
        settings.inference_steps,
    )
    settings.number_of_images = user_value(
        int,
        f"Number of images per batch ({settings.number_of_images}): ",
        settings.number_of_images,
    )
    _batch_count = user_value(
        int,
        f"Batch count ({_batch_count}): ",
        _batch_count,
    )
    # output_format = user_value(int, f"Output format (PNG)", 1)
    print(config.lcm_diffusion_setting)


def interactive_txt2img(
    config,
    context,
):
    global _batch_count
    config.lcm_diffusion_setting.diffusion_task = DiffusionTask.text_to_image.value
    user_input = input("Write a prompt (write 'exit' to quit): ")
    while True:
        if user_input == "exit":
            exit()
        config.lcm_diffusion_setting.prompt = user_input
        for i in range(0, _batch_count):
            context.generate_text_to_image(
                settings=config,
                device=DEVICE,
            )
        user_input = input("Write a prompt: ")


def interactive_img2img(
    config,
    context,
):
    global _batch_count
    settings = config.lcm_diffusion_setting
    settings.diffusion_task = DiffusionTask.image_to_image.value
    steps = settings.inference_steps
    source_path = input("Image path: ")
    if source_path == "":
        print("Error : You need to provide a file in img2img mode")
        exit()
    settings.strength = user_value(
        float,
        f"img2img strength ({settings.strength}): ",
        settings.strength,
    )
    settings.inference_steps = int(steps / settings.strength + 1)
    user_input = input("Write a prompt (write 'exit' to quit): ")
    while True:
        if user_input == "exit":
            exit()
        settings.init_image = Image.open(source_path)
        settings.prompt = user_input
        for i in range(0, _batch_count):
            context.generate_text_to_image(
                settings=config,
                device=DEVICE,
            )
        new_path = input(f"Image path ({source_path}): ")
        if new_path != "":
            source_path = new_path
        settings.strength = user_value(
            float,
            f"img2img strength ({settings.strength}): ",
            settings.strength,
        )
        settings.inference_steps = int(steps / settings.strength + 1)
        user_input = input("Write a prompt: ")


def interactive_variations(
    config,
    context,
):
    global _batch_count
    settings = config.lcm_diffusion_setting
    settings.diffusion_task = DiffusionTask.image_to_image.value
    steps = settings.inference_steps
    source_path = input("Image path: ")
    if source_path == "":
        print("Error : You need to provide a file in Image variations mode")
        exit()
    settings.strength = user_value(
        float,
        f"Image variations strength ({settings.strength}): ",
        settings.strength,
    )
    settings.inference_steps = int(steps / settings.strength + 1)
    while True:
        settings.init_image = Image.open(source_path)
        settings.prompt = ""
        for i in range(0, _batch_count):
            generate_image_variations(
                settings.init_image,
                settings.strength,
            )
        user_input = input("Continue in Image variations mode? (Y/n): ")
        if user_input.upper() == "N":
            exit()
        new_path = input(f"Image path ({source_path}): ")
        if new_path != "":
            source_path = new_path
        settings.strength = user_value(
            float,
            f"Image variations strength ({settings.strength}): ",
            settings.strength,
        )
        settings.inference_steps = int(steps / settings.strength + 1)


def interactive_edsr(
    config,
    context,
):
    source_path = input("Image path: ")
    if source_path == "":
        print("Error : You need to provide a file in EDSR mode")
        exit()
    while True:
        output_path = FastStableDiffusionPaths.get_upscale_filepath(
            source_path,
            2,
            config.generated_images.format,
        )
        result = upscale_image(
            context,
            source_path,
            output_path,
            2,
        )
        user_input = input("Continue in EDSR upscale mode? (Y/n): ")
        if user_input.upper() == "N":
            exit()
        new_path = input(f"Image path ({source_path}): ")
        if new_path != "":
            source_path = new_path


def interactive_sdupscale_settings(config):
    steps = config.lcm_diffusion_setting.inference_steps
    custom_settings = {}
    print("> 1. Upscale whole image")
    print("> 2. Define custom tiles (advanced)")
    option = user_value(
        int,
        "Select an SD Upscale option (1): ",
        1,
    )
    if option not in range(1, 3):
        print("Wrong SD Upscale option!")
        exit()

    # custom_settings["source_file"] = args.file
    custom_settings["source_file"] = ""
    new_path = input(f"Input image path ({custom_settings['source_file']}): ")
    if new_path != "":
        custom_settings["source_file"] = new_path
    if custom_settings["source_file"] == "":
        print("Error : You need to provide a file in SD Upscale mode")
        exit()
    custom_settings["target_file"] = None
    if option == 2:
        custom_settings["target_file"] = input("Image to patch: ")
        if custom_settings["target_file"] == "":
            print("No target file provided, upscaling whole input image instead!")
            custom_settings["target_file"] = None
            option = 1
    custom_settings["output_format"] = config.generated_images.format
    custom_settings["strength"] = user_value(
        float,
        f"SD Upscale strength ({config.lcm_diffusion_setting.strength}): ",
        config.lcm_diffusion_setting.strength,
    )
    config.lcm_diffusion_setting.inference_steps = int(
        steps / custom_settings["strength"] + 1
    )
    if option == 1:
        custom_settings["scale_factor"] = user_value(
            float,
            f"Scale factor (2.0): ",
            2.0,
        )
        custom_settings["tile_size"] = user_value(
            int,
            f"Split input image into tiles of the following size, in pixels (256): ",
            256,
        )
        custom_settings["tile_overlap"] = user_value(
            int,
            f"Tile overlap, in pixels (16): ",
            16,
        )
    elif option == 2:
        custom_settings["scale_factor"] = user_value(
            float,
            "Input image to Image-to-patch scale_factor (2.0): ",
            2.0,
        )
        custom_settings["tile_size"] = 256
        custom_settings["tile_overlap"] = 16
    custom_settings["prompt"] = input(
        "Write a prompt describing the input image (optional): "
    )
    custom_settings["tiles"] = []
    if option == 2:
        add_tile = True
        while add_tile:
            print("=== Define custom SD Upscale tile ===")
            tile_x = user_value(
                int,
                "Enter tile's X position: ",
                0,
            )
            tile_y = user_value(
                int,
                "Enter tile's Y position: ",
                0,
            )
            tile_w = user_value(
                int,
                "Enter tile's width (256): ",
                256,
            )
            tile_h = user_value(
                int,
                "Enter tile's height (256): ",
                256,
            )
            tile_scale = user_value(
                float,
                "Enter tile's scale factor (2.0): ",
                2.0,
            )
            tile_prompt = input("Enter tile's prompt (optional): ")
            custom_settings["tiles"].append(
                {
                    "x": tile_x,
                    "y": tile_y,
                    "w": tile_w,
                    "h": tile_h,
                    "mask_box": None,
                    "prompt": tile_prompt,
                    "scale_factor": tile_scale,
                }
            )
            tile_option = input("Do you want to define another tile? (y/N): ")
            if tile_option == "" or tile_option.upper() == "N":
                add_tile = False

    return custom_settings


def interactive_sdupscale(
    config,
    context,
):
    settings = config.lcm_diffusion_setting
    settings.diffusion_task = DiffusionTask.image_to_image.value
    settings.init_image = ""
    source_path = ""
    steps = settings.inference_steps

    while True:
        custom_upscale_settings = None
        option = input("Edit custom SD Upscale settings? (y/N): ")
        if option.upper() == "Y":
            config.lcm_diffusion_setting.inference_steps = steps
            custom_upscale_settings = interactive_sdupscale_settings(config)
            source_path = custom_upscale_settings["source_file"]
        else:
            new_path = input(f"Image path ({source_path}): ")
            if new_path != "":
                source_path = new_path
            if source_path == "":
                print("Error : You need to provide a file in SD Upscale mode")
                exit()
            settings.strength = user_value(
                float,
                f"SD Upscale strength ({settings.strength}): ",
                settings.strength,
            )
            settings.inference_steps = int(steps / settings.strength + 1)

        output_path = FastStableDiffusionPaths.get_upscale_filepath(
            source_path,
            2,
            config.generated_images.format,
        )
        generate_upscaled_image(
            config,
            source_path,
            settings.strength,
            upscale_settings=custom_upscale_settings,
            context=context,
            tile_overlap=32 if settings.use_openvino else 16,
            output_path=output_path,
            image_format=config.generated_images.format,
        )
        user_input = input("Continue in SD Upscale mode? (Y/n): ")
        if user_input.upper() == "N":
            exit()