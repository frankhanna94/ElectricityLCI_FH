# This module includes a set of methods to streamline running and
# rolling up older versions of electricity LCI configurations (e.g., 2016)

# Approach - post processing step
# 1. Import JSON-LD to a new openLCA database
# 2. Connect to openLCA database
# 3. Rollup processes
#   3.1. User input - rollup everything or only consumption mixes?
#   3.2. Roll-up selected processes
#       If only consumption mix processes --> UUIDs never change in eLCI
# 4. Delete all old processes and product systems (everything except new SPs)

# Functions needed - main and helper functions
# Main function
#   loop through processes
#   roll-up selected processes (Depending on user input) --> helper function from N-CLAD src
#   rename the rolled up processes to append the year --> helper function to be created
#   delete processes by uuid --> helper function to be created
#   delete product systems by uuid --> helper function to be created

# import dependencies
import os
import logging
import uuid
import pandas as pd
import datetime

import olca_schema as olca
import olca_schema.units as o_units

# GLOBALS
consumption_mix_processes = [
    "75d4be66-12a7-30b3-bc57-fa724c941b0e",
    "820dce70-1ea5-3b8a-b551-e8660e280f9f",
    "37733d38-be37-32eb-a6ad-4f119294136f",
    "9f6a16c6-3df8-39f0-8b4e-af72c0e663ca",
    "a2522eb7-a557-3242-8d26-042fc4b41195",
    "8aaa2df9-e6e6-3774-91a1-553bed6a719a",
    "696cf4c2-3b38-37c2-81dc-187b767b4a1e",
    "11b43f23-fa67-3d22-9e80-8951c69d7b5e",
    "13ef9dff-c849-324e-a964-25fe48907c8c",
    "b16ca0d0-3f5c-3a24-a398-3bda3ffe06bd",
    "1744d0a0-5348-316f-ae28-9543f3a03d1d",
    "cc2dd726-d99f-3914-9c02-65b0ae57102a",
    "f268f3ff-e1c6-303b-b7f2-7290cc7b98d6",
    "72c31c1e-ae3f-32a3-89a9-8066379d5b3b",
    "c3557d8e-c91a-3e9c-bb90-47fe970a00ec",
    "46535c58-2c1d-3561-a5bb-a008b9c959d8",
    "c69563ec-887a-35ca-acc5-820ae0ba5f72",
    "337fc42a-81b5-3d8b-b98f-614d417bc11f",
    "dc255d13-6512-372d-8738-48739679d529",
    "34b70fb7-6d4a-3eae-99dc-9a3b4b4624df",
    "5c230c62-5c0e-36d5-bc0a-1e4d28ef30ab",
    "b9454a38-b53a-3d40-b121-058f233f9643",
    "5fbe46bd-265a-3a59-98fe-c74a1c223877",
    "690d5f79-401d-3d30-9eb3-944df1715f75",
    "7bd56448-965a-3e54-bf7f-f28608f4fe7a",
    "afb0a8ed-7e33-37ec-aa70-2286f8f84935",
    "9e5f30e4-76b0-307d-b75b-429fe18bb4e1",
    "f03e070d-463f-3d2f-82aa-b5bffa1cabd8",
    "6868698b-57f5-3ae2-bbb1-f3b160ef9945",
    "b683482f-bae9-3b2f-a7c8-ed8964094c04",
    "99661c17-082b-33a2-8d0e-8331d19831e2",
    "2789aa03-b05c-3374-9aaa-12d1a20a6a55",
    "4537d7cd-1dbf-37b5-a4c6-1a1f2c19a1de",
    "81511323-42bf-3f8e-9c9d-31d6d50e935d",
    "610df26a-4b74-30c3-be75-7af4e6021ab9",
    "ada5f6f3-eba8-35da-9ec4-df88c836ab68",
    "4502179f-467b-3952-b284-863fecbd2acb",
    "5b2599cc-deb4-3602-a484-1af00f05d770",
    "11b087d8-8981-373b-aef7-43a4a17cbe8e",
    "d640a8aa-93b2-3d0e-8012-24b79ead9694",
    "f80d17d0-8756-3933-9b8f-67f55495b5db",
    "73cf723e-ab4a-3ae1-9a1e-a34364cea714",
    "653d2bf8-9ace-33fd-a537-7b10dd2499c0",
    "026104f5-0d33-34d3-acf3-d92e6035156f",
    "22bf4ba1-b400-3ba2-bc0a-184a44694cc5",
    "81320fab-eef5-39b4-bf21-7cc2edb539c9",
    "64ddc11d-3d2b-3e2b-8c21-5fc1d11febfd",
    "3862d7de-4942-35b6-bf7b-6dc22ea6305f",
    "82651099-95cb-3377-b030-045e4cbed506",
    "f791afbb-cde3-3964-95f8-1865271d97c0",
    "688bedec-5571-3280-828d-4245f2b06f47",
    "85c361e4-4861-38d7-9441-accd93f4cfad",
    "98b00934-c348-3833-a480-7100e153e41e",
    "27e90eb9-c0a9-3c43-9f9c-839b703670c3",
    "ec6a9894-9221-34d6-9814-b0179435bac8",
    "64b4786b-0d0e-3f41-b49f-d51486884c98",
    "f41111d1-1668-325a-abd2-a40af161e35d",
    "9aa4d22e-c29e-35ac-b81d-1908de7be42b",
    "b42ca74f-a649-32d5-9a9f-6a9846e7af51",
    "231ed52a-5ec4-3216-9f16-3cbf4a7bb794",
    "db0fc1d8-d8ca-3875-8058-f9b4b4d01ac5",
    "91ba7e39-5ec0-3f25-b643-6b36dfd084b6",
    "f4ced9c2-776a-3137-9f04-af771f34cb8c",
    "5ac61f8b-20d0-3a99-a4a0-c888d8d23423",
    "1eba69d4-62c4-3a1b-ba13-d7f2893c1f28",
    "4a1816ca-5263-383b-bfbe-beec1acbb9c2",
    "c3096d7d-a9c4-3a39-9814-65304089d770",
    "476cb9dd-c521-3a06-8d12-c6cf472c0be1",
    "3d4710d5-b80d-38ca-b381-fd2125b0f542",
    "46626051-54c2-3142-9577-355822757d80",
    "3b623b7e-b22b-3903-9670-7aaac965357d",
    "5c13cc4e-b1eb-3fca-a291-b2891bd253a0",
    "ccbab212-154f-3421-b714-c24346bece5b",
    "f21316ee-5206-3cb6-80ac-9516cfd74abf",
    "f6579b75-679d-38ed-b7b8-e5026887b008",
    "6ea4ba30-2cef-3a68-99d7-efb3a2088e06",
    "483aa8c9-12d2-3a42-91f1-09085f3c9c6b",
    "081c824a-a8a4-3958-8e6e-1bf18e1841f2",
    "39a94f2a-03f7-38ca-9cf1-71a839287487",
    "668f4318-8e2e-35f1-82ab-4647e7bd42a8",
    "996438f6-ff4b-3c11-a44a-cc64ce7a7b30",
    "0082cc36-0aa6-3ff2-acf5-a2765411b57a",
    "0f3c15c4-b592-37c8-89c1-cace88810e03",
    "20dbe919-4e53-3360-a0d1-246de37e748d",
    "2ef4fd99-1137-3f5d-b3d6-fbe1930b2d7d",
    "163650de-0ebd-3f9b-b7f0-338701161e8b",
    "cab7d877-234b-3e69-8b8e-240cb7196021",
    "a9420547-6281-38fe-bb48-a32546ed849f",
    "79ea9941-224c-30bd-969d-4032cfaa8005",
    "d0481c35-49ba-3f00-9213-1b087ac9198e",
    "e06c46bf-e2d6-33bf-90e7-1f90eeb98dcb",
    "c06b0df8-1d75-39c6-aa87-49100c889658",
    "b74ffbc4-0dab-3f84-977f-531e3c5008c4",
    "9ce1f4d7-caf4-3f29-9208-b54a3803b295",
    "00f828c8-2aa5-3e86-a2cd-fabe0489d245",
    "ec5c89b7-509e-3fd7-9308-f51554c1b529",
    "ef86245c-837b-3555-b556-d1f5346f2f76",
    "1cca2393-ee00-3fa3-9884-986d39730113",
    "db2921f6-74d4-3e2f-9524-417d2e19c826",
    "6c24ac2c-dd77-3dff-a8cc-90054528ec3f",
    "7cbef411-51cd-3d49-bee8-49fdc4ef98cf",
    "a32b02de-c81f-3fba-bb48-58f5f5d9c2c8",
    "6334c6ab-2295-313a-8cbd-a8e86e846232",
    "07802327-0d38-3d14-a4b0-c71554da61d4",
    "7faaf99b-7a36-3c72-a485-dde4df9fd525",
    "02e2f5b0-74ac-3c4b-a691-d7b1ad5e3646",
    "9f160965-7cd6-3f2a-be2f-30e99e8d9696",
    "afd157a1-c37c-3f33-bd41-227114c381f8",
    "a9eed0a6-6813-3083-881a-ce9f6856fe0f",
    "3aed3164-bbec-3d54-a483-508a7765a9fd",
    "fdf79353-fbd3-30b4-aa15-267a212b9da4",
    "4a9358dd-5c89-3164-a6c0-40e40f587350",
    "1ea0668d-d780-3a6a-a4bc-3447358060df",
    "39890793-d56a-3616-9da0-be3a79f81aff",
    "73d35f2d-1256-3d90-b387-e6cd92f1b9b0",
    "018019c9-b57c-3bc7-ae20-4fcb66243960",
    "40ea324d-0b17-3f38-babd-6c1d93b99e3d",
    "b62e0b13-f036-3b07-aa74-c36a6c505d1a",
    "37b87ceb-2e31-3d38-baaa-84f148287d2f",
    "d29a1cb4-f929-3f9d-8aee-045fdae8cab4",
    "52249d0b-6d45-3f74-87fd-e62d8ddf000a",
    "112d97d5-63cb-324a-9413-6e64d2a6694b",
    "5739eaff-4c35-359d-8a18-cbc9149bde83",
    "dd3b1db6-c80a-3cc6-af99-237ef7f04606",
    "6ddae3ea-187e-3c07-9e17-29a65a5927a7",
    "ff87ed0b-db00-312a-bca8-2b9f2d3b3456",
    "ba6c7a86-9e38-357a-a11b-6fd0945a2e5e",
    "cd9c001f-0160-3ae9-82a5-81decd6beb4f",
    "d1e20ef2-31c8-3305-969a-e008341a50e1",
    "739a9cbd-7189-3c4b-ae7b-8b756e99bcfb",
    "a2a22977-2b95-358b-90ca-ca7f1fbeb167",
    "28382a88-b2b2-3cfe-985e-659290858e70",
    "75f0af0b-abe3-36f4-ae05-2fdf13c7167b",
    "3b36f413-39cb-3dc2-b513-fd2b1b4149c1",
    "b55ec9c6-062f-3cd6-aee0-940f3c589726",
    "6f718d2f-46c4-362a-a196-c261265ee736",
    "33c05d14-fa45-3b60-bef8-768168b22db9",
    "e4fcd21b-a651-31c8-a123-ff308a80e080",
    "0033b245-c828-3fe4-ba32-1e35bc4d30ca",
    "b47455f1-fc68-33b2-a2a8-217485ef8bba",
    "763f16bd-1c1e-336a-acc0-626123547161",
    "75132c61-a7bd-3cf4-a377-1e97e124becd",
]

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), ".netl_dd")
"""str : The hidden output folder in the user's home directory."""

QA_UNIT_CSV = os.path.join(OUTPUT_DIR, "qa_missing_units.csv")
"""str : The CSV file path for tracking missing units."""


# Main function
def run_rollup_electricitylci(
    client, date=None, rollup_consumption_only=True, impact_method_uuid=None
):
    """
    Run the rollup of electricity LCI processes in an openLCA database.

    Parameters:
    - client: An instance of the openLCA client to connect to the database.
    - date: The date to append to the new name of the rolled up process.
    - rollup_consumption_only: A boolean indicating whether to roll up only consumption mix processes (True) or all processes (False).

    Returns:
    None
    """
    if date is None:
        logging.warning(
            "No date provided for rollup. "
            "The rolled up processes will not have a date appended to their names."
        )

    if impact_method_uuid is None:
        logging.warning(
            "No impact method UUID provided. "
            "Impact values will not be compared between original and rolled up processes."
        )

    # Step 1: Get list of processes and product systems uuids
    original_processes = client.get_spec_ids(olca.Process)
    original_product_systems = client.get_spec_ids(olca.ProductSystem)

    # Step 2: Rollup processes based on user input
    if rollup_consumption_only:
        # Roll up only consumption mix processes
        logging.info("Rolling up only consumption mix processes...")
        rollup_consumption_mix_processes(
            client, date, impact_method_uuid, new_name=None
        )
    else:
        # Roll up all processes
        logging.info("Rolling up all processes...")
        rollup_all_processes(
            client, original_processes, date, impact_method_uuid, new_name=None
        )

    # Step 3: Delete old processes
    for process in original_processes:
        delete_process(client, process)

    # Step 4: Delete all product systems
    for ps in original_product_systems:
        delete_product_system(client, ps)

    return


# helper functions


def rollup_consumption_mix_processes(client, date, impact_method_uuid, new_name):
    """
    Roll up only the consumption mix processes in the openLCA database.

    Parameters:
    - client: An instance of the openLCA client to connect to the database.
    - date: The date to append to the new name of the rolled up process.

    Returns:
    None
    """
    # Implementation for rolling up consumption mix processes
    for process_uuid in consumption_mix_processes:
        roll_up_process(client, process_uuid, date, impact_method_uuid, new_name)
    return None


def rollup_all_processes(client, process_uuids, date, impact_method_uuid, new_name):
    """
    Roll up all processes in the openLCA database.

    Parameters:
    - client: An instance of the openLCA client to connect to the database.
    - process_uuids: A list of UUIDs of the processes to be rolled up.
    - date: The date to append to the new name of the rolled up process.

    Returns:
    None
    """
    # Implementation for rolling up all processes
    for process_uuid in process_uuids:
        roll_up_process(client, process_uuid, date, impact_method_uuid, new_name)
    return None


def roll_up_process(
    client,
    process_uuid,
    date,
    prov_linking="only_defaults",
    impact_method_uuid=None,
    new_name=None,
):
    """
    Helper function to roll up a process into a product system.

    Parameters
    ----------
    client : NetlOlca
        An instance of NetlOlca class.
    process_uuid : str
        The UUID of the process to be rolled up.
    date : str
        The date to append to the new name of the rolled up process.
    prov_linking : str (optional)
        The provenance linking option to use for the analysis.
        Options: ignore_defaults, prefer_defaults, only_defaults
        (default: "only_defaults")
    impact_method_uuid : str (optional)
        The UUID of the impact method to use for the analysis.
        None: the default impact method will be used
        (default: None)
    new_name : str (optional)
        The new name for the rolled up process.

    Returns
    -------
    tuple
        A tuple containing the UUID of the rolled up process and the impact
        values for the process.

        - str: The UUID of the rolled up process.
        - pd.DataFrame: The impact values for the process.
    """
    # get process object
    p = client.query(olca.Process, process_uuid)
    # check if process already 'LCI_RESULT' type, skip rollup
    original_process_type = p.process_type
    if original_process_type == olca.ProcessType.LCI_RESULT:
        logging.warning(
            f"Process {process_uuid} is already of type 'LCI_RESULT'. "
            "Skipping roll-up."
        )
        # update process name
        original_process_name = p.name
        if new_name is None:
            new_name = original_process_name
        if date is not None:
            new_name += f" - {date}"
        p.name = new_name
        # update process uuid
        process_category = p.category
        new_uuid = _uid(original_process_type, process_category, new_name)
        p.id = new_uuid
        client.client.put(p)

    else:
        # run analysis for the process
        logging.info("Roll-up -- " "Evaluating original process to extract LCI")
        all_flows_df, original_impact_values = run_analysis_for_process(
            client, process_uuid, prov_linking, impact_method_uuid
        )

        # Get the process name and description; update name for roll up process.
        process_description = p.description
        original_process_name = p.name
        if new_name is None:
            new_name = original_process_name
        if date is not None:
            new_name += f" - {date}"
        process_category = p.category

        # create new process using all flows df
        logging.info("Roll-up -- Generating new roll-up process")
        quant_ref_flow = client.get_quantitative_reference_flow(process_uuid)
        new_uuid = create_new_system_process(
            client,
            all_flows_df,
            new_name,
            process_description,
            quant_ref_flow,
            "LCI_RESULT",
            process_category,
        )

        # run analysis for the rolled up process
        logging.info("Roll-up -- Evaluating rolled up process to extract impact values")
        _, rollup_impact_values = run_analysis_for_process(
            client, new_uuid, prov_linking, impact_method_uuid
        )

    # compare the impact values of the original and rolled up processes
    # the validation will only happen if the user provides an impact method uuid
    if (
        original_process_type is not olca.ProcessType.LCI_RESULT
        and impact_method_uuid is not None
    ):
        logging.info(
            "Roll-up -- " "Comparing impact values of original and rolled up processes"
        )
        for _, row in original_impact_values.iterrows():
            idx = rollup_impact_values.index[
                rollup_impact_values["impact_category"] == row["impact_category"]
            ][0]
            warning = 0
            logging.info(
                f"Impact Category: {row['impact_category']}, "
                f"Original Process Impact: {row['amount']}, "
                "Rolled Up Process Impact: "
                f"{rollup_impact_values.loc[idx, 'amount']}"
            )
            a = row["amount"]
            b = rollup_impact_values.loc[idx, "amount"]
            if a != 0 and b != 0:
                p_diff = abs(a - b) * 100 / (a)  # calculate percent difference
                if p_diff > 0.01:
                    logging.warning(
                        f"Impact value mismatch for {row['impact_category']} \n"
                        f"Process name: {original_process_name} \n"
                        f"Original: {row['amount']} \n"
                        f"Rolled up: {rollup_impact_values.loc[idx, 'amount']}"
                    )
                    warning += 1
        if warning == 0:
            logging.info(
                "Roll-up -- Roll-up process created successfully"
                " | No mismatch found in impact values"
            )
    else:
        original_impact_values = None
        rollup_impact_values = None
    logging.info(
        f"Roll-up -- Original process UUID: {process_uuid}"
        f" | Roll-up UUID: {new_uuid}"
    )

    return new_uuid, original_impact_values, rollup_impact_values


def create_new_system_process(
    client,
    flows_df,
    process_name,
    process_description,
    quant_ref_flow,
    process_category,
):
    """
    Helper function to create a new process in openLCA.

    Parameters
    ----------
    client : NetlOlca
    flows_df : pd.DataFrame
    process_name : str
    process_description : str
    quant_ref_flow : olca-schema.Exchange
        An exchange object associated as quantitative reference flow,
        or NoneType (if method fails to find process or no flows are
        labeled as quantitative reference).
    process_category : str

    Returns
    -------
    olca-schema.Ref
        A reference object to the newly created process.

    Notes
    -----
    1.  This function is modified from the original function adopted from the
        lca-prommis work.
        Git Repository: https://github.com/KeyLogicLCA/lca-prommis
    2.  Core modification: The created process only expect elementary flows and
        a reference product flow - no product or waste flows (e.g.,
        technosphere flows)
    3.  The function assumes that client is initialized before running this
        function by connecting to openLCA via IPC service.
    """
    # Create empty process
    new_p = create_empty_process(
        process_name, process_description, "LCI_RESULT", process_category
    )

    # Create exchanges
    exchanges = []

    # Overwrite internal ID to 1
    quant_ref_flow.internal_id = 1
    exchanges.append(quant_ref_flow)

    # loop through the dataframe and create exchanges for elementary flows
    ex_id = 2

    # loop through the dataframe and create exchanges for elementary flows
    for _, row in flows_df.iterrows():
        name = row["flow_name"]
        unit = row["unit"]
        amount = row["amount"]
        is_input = row["is_input"]
        flow_uuid = row["flow_uuid"]
        flow_type = row["flow_type"]

        if unit is None:
            logging.warning(f"{name} | {flow_uuid} has no unit and will be skipped...")
            unit_out_str = (
                f"{process_name},{process_category},{flow_type},{name},"
                f"{amount},{is_input},{flow_uuid}\n"
            )
            with open(QA_UNIT_CSV, "a") as f:
                f.write(unit_out_str)
            # NOTE - seems like some elementary flows have no unit, which is
            # creating a problem when creating exchanges.
            continue

        flow_property = o_units.property_ref(unit)
        if flow_property is None:
            logging.warning(
                f"{name} | {flow_uuid} has no flow property " "and will be skipped..."
            )
            unit_out_str = (
                f"{process_name},{process_category},{flow_type},{name},"
                f"{amount},{is_input},{flow_uuid}\n"
            )
            with open(QA_UNIT_CSV, "a") as f:
                f.write(unit_out_str)
            continue
        try:
            exchange = create_elementary_flow_exchange(
                client,
                ex_id,
                flow_uuid,
                unit,
                amount,
                is_input,
                is_quantitative_reference=False,
            )
            exchanges.append(exchange)
            ex_id += 1
        except Exception as e:
            raise ValueError(f"Error creating exchange: {e}")

    # add exchanges to process
    new_p.exchanges = exchanges
    new_p.category = process_category
    # new process uuid
    new_process_uuid = new_p.id

    # save process to openLCA
    if client.add(new_p):
        # Update the NetlOlca class's log of Process UUIDs
        client._add_to_spec_ids(
            olca.Process,
            [
                new_process_uuid,
            ],
        )

    return new_process_uuid


def create_ps(client, process_uuid, prov_linking="only_defaults"):
    """Helper function to create a product system in openLCA.

    Parameters
    ----------
    client : NetlOlca
        An NetlOlca class instance connected to openLCA via IPC service.
    process_uuid : str
        The universally unique identifier to a process, which will become
        the reference process to the created product system.
    prov_linking: olca.ProviderLinking
        The provider linking configuration for the product system.
        Options: ignore_defaults, prefer_defaults, only_defaults

    Returns
    -------
    olca-schema.Ref
        A reference object to the newly created product system.

    Notes:
    ------
    The providers linking configuration is hard coded in the function to only
    use default providers
    """
    # create product system with name of process
    process_ref = client.query(olca.Process, process_uuid).to_ref()

    # setup provider linking
    prov_linking_map = {
        "ignore_defaults": olca.ProviderLinking.IGNORE_DEFAULTS,
        "prefer_defaults": olca.ProviderLinking.PREFER_DEFAULTS,
        "only_defaults": olca.ProviderLinking.ONLY_DEFAULTS,
    }

    linking_config = olca.LinkingConfig(
        cutoff=None,
        prefer_unit_processes=True,
        provider_linking=prov_linking_map[prov_linking],
    )
    product_system_ref = client.client.create_product_system(
        process_ref, linking_config
    )

    return product_system_ref


def create_empty_process(process_name, process_description, process_type, category):
    """Helper function to create an empty process.

    Parameters
    ----------
    process_name : str
        The name of the process.
    process_description : str
        The description of the process.
    process_type : str
        The type of the process.
        Options: 'UNIT_PROCESS', 'LCI_RESULT'

    Returns
    -------
    olca.Process
        A process object.

    Notes
    -----
    This function is adopted from the lca-prommis work.
    Git Repository: https://github.com/KeyLogicLCA/lca-prommis
    """
    if process_type == "UNIT_PROCESS":
        process_type = olca.ProcessType.UNIT_PROCESS
    elif process_type == "LCI_RESULT":
        process_type = olca.ProcessType.LCI_RESULT
    else:
        process_type = olca.ProcessType.UNIT_PROCESS

    process_id = _uid(process_type, category, process_name)

    process = olca.Process(
        id=process_id,
        name=process_name,
        description=process_description,
        process_type=process_type,
        version="1.0.0",
        last_change=datetime.datetime.now().isoformat(),
        category=category,
    )

    return process


def create_elementary_flow_exchange(
    client, ex_id, flow_uuid, unit, amount, is_input, is_quantitative_reference
):
    """Helper function to create and return an `olca.Exchange` object.

    Parameters
    ----------
    client : NetlOlca
        An instance of NetlOlca class.
    ex_id : int
        Internal ID for the exchange.
    flow_uuid : str
        Flow universally unique identifier.
    unit : olca.Unit, str
        A Unit class instance or unit name.
        Falls bac to the flow's reference unit.
    amount : int, float
        Numeric flow amount. #TODO - doesn't work with formulas
    is_input : bool
        Whether the flow is an input or output.
    is_quantitative_reference : bool
        Whether the flow is a quantitative reference flow.

    Returns
    -------
    olca.Exchange
        Exchange object.

    Raises
    ------
    ValueError
        Failed to find flow or flow property in openLCA database or the flow
        type is not an elementary flow type.

    Note
    ----
    1.  This function is modified from the original function adopted from the
        lca-prommis work.
        Git Repository: https://github.com/KeyLogicLCA/lca-prommis
    """
    # Get flow and make additional checks
    # - it exists and it is an elementary flow
    flow: olca.Flow = client.query(olca.Flow, flow_uuid)
    if flow is None:
        raise ValueError(f"Flow not found: {flow_uuid}")
    if flow.flow_type != olca.FlowType.ELEMENTARY_FLOW:
        raise ValueError("Provided flow is not an ELEMENTARY_FLOW")

    # Get reference flow property.
    # In olca_schema, the flow property falls under flow.flow_properties
    # the reference flow property is the one with is_ref_flow_property = True
    # this would be the one that help define the unit of the flow (e.g., mass,
    # volume, energy, etc.), and flow.flow_properties is a list of
    # FlowPropertyFactors; we want the one that is_ref_flow_property = true

    flow_property = o_units.property_ref(unit)
    if flow_property is None:
        flow_property = o_units.property_ref(unit.lower())
    if flow_property is None:
        raise ValueError(
            "The flow property is not found in the flow. "
            "Adjust your unit or select another flow"
        )

    # Set unit.
    # If we pass the unit as a string, we need to resolve it to the unit object.
    # The reason why we have the _resolve_unit function is that if we pass the
    # unit as an object, we can use it directly but the challenge is that the
    # unit object is having have an olca.Unit object that belongs to the same
    # unit group as the flow’s (reference) flow property

    # Create exchange
    exchange = client.make_exchange()
    exchange.flow = flow

    # Set the FlowProperty reference on the exchange
    exchange.flow_property = flow_property
    exchange.unit = o_units.unit_ref(unit)
    if exchange.unit is None:
        exchange.unit = o_units.unit_ref(unit.lower())
    exchange.amount = float(amount)
    exchange.is_input = is_input
    exchange.is_quantitative_reference = is_quantitative_reference
    exchange.internal_id = ex_id

    return exchange


def run_analysis_for_process(client, process_uuid, impact_method_uuid=None):
    """This method runs an analysis in openLCA for a process.
    The analysis is run by creating a product system for the process,
    and running the analysis for the product system.

    Parameters
    ----------
    client : NetlOlca
        An instance of NetlOlca class.
    process_uuid : str
        The UUID of the process to analyze.
    impact_method_uuid : str, optional
        The UUID of the impact method to use for the analysis.

    Returns
    -------
    tuple
        A tuple containing the dataframe and the sum of LCI amounts for the
        process.

        - pd.DataFrame: A dataframe containing the flows
        - pd.DataFrame: The impact values for the process.

    Notes
    ------
    The user can provide a custom impact method UUID to use for the analysis.

    The providers linking configuration is hard coded in the function to only
    use default providers.
    """
    # create product system
    try:
        product_system = create_ps(client, process_uuid)
    except Exception as e:
        raise ValueError(f"Error creating product system: {e}")

    # calculate product system and extract result
    try:
        result = run_analysis_for_product_system(
            client, product_system.id, impact_method_uuid
        )
    except Exception as e:
        raise ValueError(f"Error compiling results: {e}")

    # make sure the result is generated
    result.wait_until_ready()
    # TODO: use the ReturnState to check and print errors, if any exist

    # Get all flows
    all_flows = result.get_total_flows()
    all_flows_df = pd.DataFrame(all_flows)
    all_flows_df = all_flows_df.apply(_extract_flow_info, axis=1)

    if impact_method_uuid is not None:
        try:
            impact_assessment_results = pd.DataFrame(result.get_total_impacts())
            impact_values = impact_assessment_results
            for idx, row in impact_values.iterrows():
                impact_values.loc[idx, "impact_category"] = row["impact_category"][
                    "name"
                ]
        except Exception as e:
            raise ValueError(f"Error getting impact assessment results: {e}")
    else:
        impact_values = None

    result.dispose()

    return all_flows_df, impact_values


def _extract_flow_info(row):
    """Helper function to extract flow information from the result object.

    The result object has two class attributes, 'amount' and 'envi_flow'.
    This method extracts relevant data from the 'envi_flow' (i.e., flow name,
    unit, is input, flow UUID, and flow type) along with flow amount.

    Parameters
    ----------
    row : dict
        A row from the result object.

    Returns
    -------
    pd.Series
        A series containing the flow information.

    Notes
    -----
    This function is generated by ChatGPT.
    """
    f = row["envi_flow"]["flow"]  # nested flow info
    return pd.Series(
        {
            "flow_name": f["name"],
            "unit": f["ref_unit"],
            "amount": row["amount"],
            "is_input": row["envi_flow"]["is_input"],
            "flow_uuid": f["id"],
            "flow_type": (
                f["flow_type"].value
                if hasattr(f["flow_type"], "value")
                else f["flow_type"]
            ),
        }
    )


def _uid(*args):
    """Generate UUID from the MD5 hash of a namespace identifier and a name.

    This method uses OID namespace, which assumes that the name is an ISO OID.
    Essentially, two strings are hashed together to create a UUID and, if the
    same namespace and path are given again, the same UUID would be returned.

    Warning
    -------
    The UUIDs generated by this method are version 3, which is different
    from standard processes defined elsewhere (e.g., DQSystems and Units).

    Parameters
    ----------
    args : tuple
        A tuple of key words representing a path (order matters).
        The path is a string with each argument separated by a forward slash.
        For flows, the path is 'modeltype.flow', flow name, compartment, and
        unit.
        For processes, the path is 'modeltype.process', process category,
        location, and name.

    Returns
    -------
    str
        A version 3 universally unique identifier (UUID)
    """
    path = "/".join([str(arg).strip() for arg in args]).lower()
    logging.debug(path)
    return str(uuid.uuid3(uuid.NAMESPACE_OID, path))


def run_analysis_for_product_system(client, ps_uuid, impact_method_uuid):
    """
    Helper function to run the analysis for a product system in openLCA.

    Parameters
    ----------
    client : olca_ipc.Client
        The IPC client object.
    ps_uuid : str
        The UUID of the product system.
    impact_method_uuid : str (optional)
        The UUID of the impact method.

    Returns
    -------
    lcia_result : olca_schema.LciaResult
        The LCA result.
    """
    # Define the impact method

    # In this project, the method is defined in a pre-setup database
    # as such, the uuid of the method is less likely to change
    # define method using uuid
    if not isinstance(impact_method_uuid, str):
        impact_method_ref = None
    else:
        # NOT A REFERENCE OBJECT
        impact_method_ref = client.query(olca.ImpactMethod, impact_method_uuid)

    # Define product system object
    # NOT A REFERENCE OBJECT
    ps_ref = client.query(olca.ProductSystem, ps_uuid)
    qre = client.get_quant_ref_flow(ps_ref.ref_process.id)

    # build the calculation setup
    # https://greendelta.github.io/olca-schema/classes/CalculationSetup.html
    setup = olca.CalculationSetup()
    setup.allocation = olca.AllocationType.USE_DEFAULT_ALLOCATION
    setup.amount = qre.amount
    setup.flow_property = qre.flow_property
    setup.impact_method = impact_method_ref
    setup.nw_set = None
    setup.parameters = None  # no parameters are considered in the current model
    # this can be incorporated in the future
    # TODO: check parameter_redef
    setup.target = ps_ref.to_ref()
    setup.unit = qre.unit
    setup.with_costs = False  # no costs are considered in the current model
    setup.with_regionalization = False  # regionalization is not considered in
    # the current model

    # Run and Generate Result
    result = client.client.calculate(setup)

    # delete the product system
    delete_product_system(client, ps_uuid)

    return result


def delete_product_system(client, ps_uuid):
    """Helper function to delete a product system"""
    psref = client.query(olca.ProductSystem, ps_uuid).to_ref()
    client.client.delete(psref)
    return True


def delete_process(client, process_uuid):
    """Helper function to delete a process"""
    pref = client.query(olca.Process, process_uuid).to_ref()
    client.client.delete(pref)
    return True
