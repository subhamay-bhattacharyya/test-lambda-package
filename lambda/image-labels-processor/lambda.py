"""
AWS Lambda boilerplate handler.

Entry point: lambda.handler
Runtime:     Python 3.x (standard library only, no third-party dependencies)
"""

import json
import boto3
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from io import BytesIO
from structured_logging import inject_lambda_context, logger


def _response(status_code: int, body: dict) -> dict:
    """Build an API Gateway-compatible proxy response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def detect_labels(photo, bucket):
    """Detect labels in an S3 image with Rekognition and draw bounding boxes on it."""
    # Create a Rekognition client
    client = boto3.client("rekognition")

    # Detect labels in the photo
    response = client.detect_labels(
        Image={"S3Object": {"Bucket": bucket, "Name": photo}},
        MaxLabels=10,
    )

    # Log detected labels
    logger.info("Detected labels", extra={"photo": photo, "bucket": bucket})
    for label in response["Labels"]:
        logger.info(
            "Label detected",
            extra={"label": label["Name"], "confidence": label["Confidence"]},
        )

    # Load the image from S3
    s3 = boto3.resource("s3")
    obj = s3.Object(bucket, photo)
    img_data = obj.get()["Body"].read()
    img = Image.open(BytesIO(img_data))

    # Display the image with bounding boxes
    plt.imshow(img)
    ax = plt.gca()
    for label in response["Labels"]:
        for instance in label.get("Instances", []):
            bbox = instance["BoundingBox"]
            left = bbox["Left"] * img.width
            top = bbox["Top"] * img.height
            width = bbox["Width"] * img.width
            height = bbox["Height"] * img.height
            rect = patches.Rectangle(
                (left, top), width, height, linewidth=1, edgecolor="r", facecolor="none"
            )
            ax.add_patch(rect)
            label_text = (
                label["Name"] + " (" + str(round(label["Confidence"], 2)) + "%)"
            )
            plt.text(
                left,
                top - 2,
                label_text,
                color="r",
                fontsize=8,
                bbox=dict(facecolor="white", alpha=0.7),
            )
    plt.show()

    return len(response["Labels"])


@inject_lambda_context
def handler(event, context):
    """
    Lambda entry point.

    Args:
        event:   Invocation payload (dict for JSON events, or service-specific shape).
        context: Runtime context object (request id, remaining time, etc.).

    Returns:
        A dict. Shape depends on the trigger; this returns a generic result.
    """
    logger.info("Received event", extra={"event": event})

    try:
        for record in event["Records"]:
            body = record["body"]
            # The SQS body is a JSON string containing the S3 notification
            if isinstance(body, str):
                body = json.loads(body)

            for s3_record in body["Records"]:
                bucket = s3_record["s3"]["bucket"]["name"]
                key = s3_record["s3"]["object"]["key"]
                logger.info("S3 object received", extra={"bucket": bucket, "key": key})

                label_count = detect_labels(key, bucket)
                logger.info(
                    "Labels detected", extra={"label_count": label_count, "key": key}
                )

        # ---- Your business logic goes here ----
        logger.info("Updated Deploy Lambda", extra={"repo": "owner/name", "count": 3})
        result = {"message": "Hello from Lambda!", "request_id": context.aws_request_id}
        # ---------------------------------------

        return _response(200, result)

    except ValueError as exc:
        # Expected, client-side problem (bad input).
        logger.warning("Validation error: %s", exc)
        return _response(400, {"error": str(exc)})

    except Exception:  # pylint: disable=broad-exception-caught
        # Unexpected failure: log the full traceback and return a generic 500.
        logger.exception("Unhandled error")
        return _response(500, {"error": "Internal server error"})
